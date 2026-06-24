from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class AttendanceMarkRequest(BaseModel):
    notes: str | None = None


class AttendanceResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    check_in: datetime | None
    check_out: datetime | None
    status: str
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendanceStatusResponse(BaseModel):
    id: uuid.UUID | None = None
    date: date
    check_in: datetime | None
    status: str
    notes: str | None


class AttendanceReportResponse(BaseModel):
    records: list[AttendanceResponse]
    total_present: int
    total_absent: int
    total_late: int
    total_half_day: int
    total_wfh: int
