from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance


LATE_CUTOFF_HOUR = 10


class AttendanceService:

    @staticmethod
    async def mark_attendance(
        db: AsyncSession, user_id: uuid.UUID, notes: str | None = None
    ) -> Attendance:
        today = date.today()
        result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.user_id == user_id,
                    Attendance.date == today,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if not existing.check_out:
                existing.check_out = datetime.now(timezone.utc)
            await db.flush()
            await db.refresh(existing)
            return existing

        now = datetime.now(timezone.utc)
        status = "late" if now.hour >= LATE_CUTOFF_HOUR else "present"

        record = Attendance(
            user_id=user_id,
            date=today,
            check_in=now,
            status=status,
            notes=notes,
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)
        return record

    @staticmethod
    async def get_today_status(
        db: AsyncSession, user_id: uuid.UUID
    ) -> Attendance | None:
        result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.user_id == user_id,
                    Attendance.date == date.today(),
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_monthly_report(
        db: AsyncSession, user_id: uuid.UUID, year: int, month: int
    ) -> dict:
        result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.user_id == user_id,
                    func.extract("year", Attendance.date) == year,
                    func.extract("month", Attendance.date) == month,
                )
            ).order_by(Attendance.date)
        )
        records = list(result.scalars().all())
        counts = AttendanceService._compute_counts(records)
        counts["records"] = records
        return counts

    @staticmethod
    async def get_yearly_report(
        db: AsyncSession, user_id: uuid.UUID, year: int
    ) -> dict:
        result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.user_id == user_id,
                    func.extract("year", Attendance.date) == year,
                )
            ).order_by(Attendance.date)
        )
        records = list(result.scalars().all())
        counts = AttendanceService._compute_counts(records)
        counts["records"] = records
        return counts

    @staticmethod
    def _compute_counts(records: list[Attendance]) -> dict:
        return {
            "total_present": sum(1 for r in records if r.status == "present"),
            "total_absent": sum(1 for r in records if r.status == "absent"),
            "total_late": sum(1 for r in records if r.status == "late"),
            "total_half_day": sum(1 for r in records if r.status == "half_day"),
            "total_wfh": sum(1 for r in records if r.status == "wfh"),
        }
