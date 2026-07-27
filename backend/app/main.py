"""FastAPI application factory and lifecycle management.

Initializes the FastAPI app, configures CORS and exception handlers,
registers all API routers, and manages startup/shutdown events including
database setup, seed data population, and cache connections.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import and_, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import async_session, engine
from app.models import (  # noqa: F401  — ensure all models are registered
    Attendance,
    ChatFeedback,
    ChatMessage,
    ChatSession,
    CompanyRole,
    CompanyRule,
    Department,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    User,
    WorkUpdate,
)
from app.services.cache_service import cache_service
from app.services.memory_service import memory_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    logger.info("Starting application")
    # ── Startup ───────────────────────────────────────────────────────────
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default data
    async with async_session() as db:
        # Seed leave types
        result = await db.execute(select(LeaveType))
        existing = {lt.name for lt in result.scalars().all()}

        leave_types_data = [
            ("casual", 18, False, 5),
            ("sick", 12, False, 3),
            ("earned", 10, True, 10),
            ("paid", 40, False, 30),
            ("unpaid", 0, False, 0),
        ]
        for name, days, carry, max_days in leave_types_data:
            if name not in existing:
                db.add(
                    LeaveType(
                        name=name,
                        days_per_year=days,
                        carry_forward=carry,
                        max_consecutive_days=max_days,
                    )
                )

        # Seed default admin
        result = await db.execute(select(User).where(User.email == "admin@hr.com"))
        if not result.scalar_one_or_none():
            admin = User(
                name="Admin",
                email="admin@hr.com",
                password_hash=hash_password("admin123"),
                role="admin",
                joining_date=date.today(),
                is_active=True,
            )
            db.add(admin)

        await db.commit()

        # Sync missing LeaveBalance for all existing users
        result = await db.execute(select(LeaveType))
        all_types = result.scalars().all()
        result = await db.execute(
            select(User).where(User.is_active == True)
        )  # noqa: E712
        all_users = result.scalars().all()
        for user in all_users:
            for lt in all_types:
                if lt.name == "unpaid":
                    continue
                result = await db.execute(
                    select(LeaveBalance).where(
                        and_(
                            LeaveBalance.user_id == user.id,
                            LeaveBalance.leave_type_id == lt.id,
                        )
                    )
                )
                if not result.scalar_one_or_none():
                    year = (
                        user.joining_date.year
                        if user.joining_date
                        else date.today().year
                    )
                    db.add(
                        LeaveBalance(
                            user_id=user.id,
                            leave_type_id=lt.id,
                            year=year,
                            total_days=lt.days_per_year,
                            used_days=0,
                            remaining_days=lt.days_per_year,
                        )
                    )
        await db.commit()

    # Connect Redis & Memory Service
    await cache_service.connect()
    # Flush stale cached data from previous server sessions
    await cache_service.delete_pattern("leave_balance:*")
    await memory_service.connect()

    logger.info("Application started successfully")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────
    await cache_service.disconnect()
    await memory_service.disconnect()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handler ────────────────────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


# ── Include routers ──────────────────────────────────────────────────────────

from app.routers import users  # noqa: E402
from app.routers import (
    attendance,
    auth,
    chat,
    departments,
    docs,
    leaves,
    work_updates,
)
from app.routers.docs import roles_router, rules_router

app.include_router(attendance.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(leaves.router)
app.include_router(work_updates.router)
app.include_router(roles_router)
app.include_router(rules_router)
app.include_router(chat.router)
app.include_router(docs.router)
app.include_router(departments.router)

logger.info("Registered %d API routers", len(app.routes))


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
    }
