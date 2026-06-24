from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import engine
from app.models import (  # noqa: F401  — ensure all models are registered
    CompanyRule,
    CompanyRole,
    Department,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    User,
    WorkUpdate,
    ChatFeedback,
)
from app.db.session import async_session
from app.services.cache_service import cache_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
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
        result = await db.execute(
            select(User).where(User.email == "admin@hr.com")
        )
        if not result.scalar_one_or_none():
            from datetime import date

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

    # Connect Redis
    await cache_service.connect()

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────
    await cache_service.disconnect()
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

from app.routers import auth, chat, leaves, roles, rules, users, work_updates  # noqa: E402

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(leaves.router)
app.include_router(work_updates.router)
app.include_router(roles.router)
app.include_router(rules.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
    }
