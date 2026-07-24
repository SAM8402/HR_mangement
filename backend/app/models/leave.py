from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

logger = logging.getLogger(__name__)


class LeaveType(Base):
    """Leave category with annual allocation and carry-forward rules."""

    __tablename__ = "leave_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        Enum(
            "casual",
            "sick",
            "earned",
            "paid",
            "unpaid",
            name="leave_type_enum",
        ),
        unique=True,
        nullable=False,
    )
    days_per_year: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    carry_forward: Mapped[bool] = mapped_column(Boolean, default=False)
    max_consecutive_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )


class LeaveBalance(Base):
    """Per-user, per-year, per-leave-type balance tracking remaining days."""

    __tablename__ = "leave_balances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leave_types.id"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remaining_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class LeaveRequest(Base):
    """Leave application with applicant, approver, date range, status, and reason."""

    __tablename__ = "leave_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leave_types.id"), nullable=False
    )
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    business_days: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "approved",
            "rejected",
            "cancelled",
            name="leave_status",
        ),
        nullable=False,
        default="pending",
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
