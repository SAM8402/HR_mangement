from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.leave import LeaveBalance, LeaveRequest, LeaveType
from app.models.user import User
from app.schemas.leave import LeaveApplyRequest
from app.utils.date_utils import calculate_business_days


class LeaveService:
    # ── Approver routing ──────────────────────────────────────────────────

    @staticmethod
    async def _find_approver(db: AsyncSession, applicant: User) -> uuid.UUID | None:
        """Route to the correct approver based on the applicant's role."""
        role = applicant.role
        dept_id = applicant.department_id

        if role == "employee":
            # Find HR or manager in the same department
            result = await db.execute(
                select(User).where(
                    and_(
                        User.department_id == dept_id,
                        User.role.in_(["hr", "manager"]),
                        User.is_active == True,  # noqa: E712
                        User.id != applicant.id,
                    )
                )
            )
            approver = result.scalars().first()
            if approver:
                return approver.id
            # Fallback: any HR user
            result = await db.execute(
                select(User).where(
                    and_(User.role == "hr", User.is_active == True)  # noqa: E712
                )
            )
            approver = result.scalars().first()
            return approver.id if approver else None

        elif role == "hr":
            result = await db.execute(
                select(User).where(
                    and_(
                        User.role == "manager",
                        User.is_active == True,  # noqa: E712
                        User.id != applicant.id,
                    )
                )
            )
            approver = result.scalars().first()
            return approver.id if approver else None

        elif role == "manager":
            result = await db.execute(
                select(User).where(
                    and_(
                        User.role == "admin",
                        User.is_active == True,  # noqa: E712
                        User.id != applicant.id,
                    )
                )
            )
            approver = result.scalars().first()
            return approver.id if approver else None

        return None

    # ── Apply ─────────────────────────────────────────────────────────────

    @staticmethod
    async def apply_leave(
        db: AsyncSession, user_id: uuid.UUID, data: LeaveApplyRequest
    ) -> LeaveRequest:
        # Fetch user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        if not user:
            raise ValueError("User not found")

        # Fetch leave type by name
        result = await db.execute(
            select(LeaveType).where(LeaveType.name == data.leave_type)
        )
        leave_type = result.scalar_one_or_none()
        if not leave_type:
            raise ValueError(f"Leave type '{data.leave_type}' not found")

        # Validate dates
        if data.from_date > data.to_date:
            raise ValueError("from_date must be before to_date")

        if data.leave_type != "unpaid":
            if data.to_date < date.today():
                raise ValueError("Cannot apply for past dates")

        business_days = calculate_business_days(data.from_date, data.to_date)
        if business_days <= 0:
            raise ValueError("Leave must span at least one business day")

        # Check balance for non-unpaid leaves
        if data.leave_type != "unpaid":
            year = data.from_date.year
            result = await db.execute(
                select(LeaveBalance).where(
                    and_(
                        LeaveBalance.user_id == user_id,
                        LeaveBalance.leave_type_id == leave_type.id,
                        LeaveBalance.year == year,
                    )
                )
            )
            balance = result.scalar_one_or_none()
            if not balance:
                raise ValueError("No leave balance found for this year")
            if balance.remaining_days < business_days:
                raise ValueError(
                    f"Insufficient leave balance. Remaining: {balance.remaining_days}, "
                    f"Requested: {business_days}"
                )

        # Find approver
        approver_id = await LeaveService._find_approver(db, user)

        leave_request = LeaveRequest(
            applicant_id=user_id,
            approver_id=approver_id,
            leave_type_id=leave_type.id,
            from_date=data.from_date,
            to_date=data.to_date,
            business_days=business_days,
            reason=data.reason,
            status="pending",
        )
        db.add(leave_request)
        await db.flush()
        await db.refresh(leave_request)
        return leave_request

    # ── Approve ───────────────────────────────────────────────────────────

    @staticmethod
    async def approve_leave(
        db: AsyncSession, leave_id: uuid.UUID, approver_id: uuid.UUID
    ) -> LeaveRequest:
        result = await db.execute(
            select(LeaveRequest).where(LeaveRequest.id == leave_id)
        )
        leave = result.scalar_one_or_none()
        if not leave:
            raise ValueError("Leave request not found")
        if leave.status != "pending":
            raise ValueError(f"Leave is already {leave.status}")
        if leave.approver_id and leave.approver_id != approver_id:
            raise ValueError("You are not the assigned approver")

        leave.status = "approved"

        # Deduct balance for non-unpaid
        result = await db.execute(
            select(LeaveType).where(LeaveType.id == leave.leave_type_id)
        )
        leave_type = result.scalar_one()
        if leave_type.name != "unpaid":
            result = await db.execute(
                select(LeaveBalance).where(
                    and_(
                        LeaveBalance.user_id == leave.applicant_id,
                        LeaveBalance.leave_type_id == leave.leave_type_id,
                        LeaveBalance.year == leave.from_date.year,
                    )
                )
            )
            balance = result.scalar_one_or_none()
            if balance:
                balance.used_days += leave.business_days
                balance.remaining_days = balance.total_days - balance.used_days

        await db.flush()
        await db.refresh(leave)
        return leave

    # ── Reject ────────────────────────────────────────────────────────────

    @staticmethod
    async def reject_leave(
        db: AsyncSession,
        leave_id: uuid.UUID,
        approver_id: uuid.UUID,
        reason: str | None = None,
    ) -> LeaveRequest:
        result = await db.execute(
            select(LeaveRequest).where(LeaveRequest.id == leave_id)
        )
        leave = result.scalar_one_or_none()
        if not leave:
            raise ValueError("Leave request not found")
        if leave.status != "pending":
            raise ValueError(f"Leave is already {leave.status}")
        if leave.approver_id and leave.approver_id != approver_id:
            raise ValueError("You are not the assigned approver")

        leave.status = "rejected"
        leave.rejection_reason = reason or "No reason provided"
        await db.flush()
        await db.refresh(leave)
        return leave

    # ── Cancel ────────────────────────────────────────────────────────────

    @staticmethod
    async def cancel_leave(
        db: AsyncSession, leave_id: uuid.UUID, user_id: uuid.UUID
    ) -> LeaveRequest:
        result = await db.execute(
            select(LeaveRequest).where(LeaveRequest.id == leave_id)
        )
        leave = result.scalar_one_or_none()
        if not leave:
            raise ValueError("Leave request not found")
        if leave.applicant_id != user_id:
            raise ValueError("You can only cancel your own leaves")
        if leave.status != "pending":
            raise ValueError(f"Cannot cancel a {leave.status} leave")

        leave.status = "cancelled"

        # Restore balance if was approved (shouldn't happen, but just in case)
        if leave.status == "approved":
            result = await db.execute(
                select(LeaveBalance).where(
                    and_(
                        LeaveBalance.user_id == user_id,
                        LeaveBalance.leave_type_id == leave.leave_type_id,
                        LeaveBalance.year == leave.from_date.year,
                    )
                )
            )
            balance = result.scalar_one_or_none()
            if balance:
                balance.used_days -= leave.business_days
                balance.remaining_days = balance.total_days - balance.used_days

        await db.flush()
        await db.refresh(leave)
        return leave

    # ── Queries ───────────────────────────────────────────────────────────

    @staticmethod
    async def get_my_leaves(db: AsyncSession, user_id: uuid.UUID) -> list[LeaveRequest]:
        result = await db.execute(
            select(LeaveRequest)
            .where(LeaveRequest.applicant_id == user_id)
            .order_by(LeaveRequest.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_pending_leaves(
        db: AsyncSession, approver_id: uuid.UUID
    ) -> list[LeaveRequest]:
        result = await db.execute(
            select(LeaveRequest)
            .where(
                and_(
                    LeaveRequest.approver_id == approver_id,
                    LeaveRequest.status == "pending",
                )
            )
            .order_by(LeaveRequest.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_leaves(db: AsyncSession) -> list[LeaveRequest]:
        result = await db.execute(
            select(LeaveRequest).order_by(LeaveRequest.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_leave_type_days(
        db: AsyncSession, type_id: uuid.UUID, days_per_year: int
    ) -> LeaveType:
        result = await db.execute(select(LeaveType).where(LeaveType.id == type_id))
        leave_type = result.scalar_one_or_none()
        if not leave_type:
            raise ValueError("Leave type not found")
        leave_type.days_per_year = days_per_year
        await db.flush()
        await db.refresh(leave_type)
        return leave_type

    @staticmethod
    async def get_balance(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
        result = await db.execute(
            select(LeaveBalance, LeaveType.name)
            .join(LeaveType, LeaveBalance.leave_type_id == LeaveType.id)
            .where(LeaveBalance.user_id == user_id)
            .order_by(LeaveType.name)
        )
        balances = []
        for row in result.all():
            balance = row[0]
            type_name = row[1]
            balances.append(
                {
                    "id": balance.id,
                    "leave_type_name": type_name,
                    "year": balance.year,
                    "total_days": balance.total_days,
                    "used_days": balance.used_days,
                    "remaining_days": balance.remaining_days,
                }
            )
        return balances
