"""Leave management request/response schemas.

Defines Pydantic models for leave application, approval/rejection,
balance queries, and leave type configuration.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LeaveApplyRequest(BaseModel):
    leave_type: str
    from_date: date
    to_date: date
    reason: str


class LeaveResponse(BaseModel):
    id: uuid.UUID
    applicant_id: uuid.UUID
    approver_id: uuid.UUID | None
    leave_type_id: uuid.UUID
    from_date: date
    to_date: date
    business_days: int
    reason: str
    status: str
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaveBalanceResponse(BaseModel):
    id: uuid.UUID
    leave_type_name: str
    year: int
    total_days: int
    used_days: int
    remaining_days: int

    model_config = {"from_attributes": True}


class LeaveActionRequest(BaseModel):
    rejection_reason: str | None = None


class LeaveTypeUpdateRequest(BaseModel):
    days_per_year: int


class LeaveTypeResponse(BaseModel):
    id: uuid.UUID
    name: str
    days_per_year: int
    carry_forward: bool
    max_consecutive_days: int

    model_config = {"from_attributes": True}
