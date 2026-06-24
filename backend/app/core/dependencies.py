"""
FastAPI Dependency Injection Module.

Provides reusable dependencies for authentication, authorization,
and database session management in route handlers.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.db.session import get_db
from app.models.user import User


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the Authorization header or token query param."""
    parsed_token = None
    if authorization and authorization.startswith("Bearer "):
        parsed_token = authorization.split(" ", 1)[1]
    elif token:
        parsed_token = token

    if not parsed_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header or token parameter",
        )

    try:
        payload = verify_token(parsed_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


def require_role(*allowed_roles: str) -> Callable:
    """Create a dependency that restricts access to specific user roles."""
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not in {list(allowed_roles)}",
            )
        return current_user

    return role_checker
