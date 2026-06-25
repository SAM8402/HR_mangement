from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.leave import LeaveBalance, LeaveType
from app.models.user import User
from app.schemas.user import UserCreate, UserListResponse, UserProfileImageUpdate, UserResponse, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


async def _create_leave_balances(
    db: AsyncSession, user_id: uuid.UUID, joining_year: int
) -> None:
    """Auto-create leave balances for a new user."""
    result = await db.execute(select(LeaveType))
    leave_types = result.scalars().all()
    year = joining_year

    for lt in leave_types:
        if lt.name == "unpaid":
            continue
        balance = LeaveBalance(
            user_id=user_id,
            leave_type_id=lt.id,
            year=year,
            total_days=lt.days_per_year,
            used_days=0,
            remaining_days=lt.days_per_year,
        )
        db.add(balance)


@router.get("", response_model=UserListResponse)
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    """List all users (admin/manager/hr only)."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=len(users),
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Create a new user (admin only). Auto-creates leave balances."""
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        department_id=data.department_id,
        joining_date=data.joining_date,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Create leave balances
    await _create_leave_balances(db, user.id, data.joining_date.year)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    """Update user details."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    # Hash password if provided
    if "password" in update_data:
        update_data["password_hash"] = hash_password(
            update_data.pop("password")
        )

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return user


@router.patch("/{user_id}/profile-image", response_model=UserResponse)
async def update_profile_image(
    user_id: uuid.UUID,
    data: UserProfileImageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a user's profile image (base64). Users can update their own, admins can update any."""
    if current_user.id != user_id and current_user.role not in ("admin", "manager", "hr"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's profile image",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.profile_image = data.profile_image
    await db.flush()
    await db.refresh(user)
    return user


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Soft-delete a user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_active = False
    await db.flush()
    return {"message": f"User {user.name} deactivated"}
