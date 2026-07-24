"""
Database Session Module.

Creates the async SQLAlchemy engine and session factory.
Provides a FastAPI dependency for request-scoped database sessions
with automatic commit/rollback handling.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
logger.info("Database engine created")

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
logger.info("SessionLocal configured")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session, committing on success and rolling back on error."""
    async with async_session() as session:
        try:
            logger.debug("Opening database session")
            yield session
            await session.commit()
            logger.debug("Closing database session")
        except Exception:
            await session.rollback()
            raise
