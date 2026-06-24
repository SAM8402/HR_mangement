from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "employee"
    department_id: uuid.UUID | None = None
    joining_date: date


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    department_id: uuid.UUID | None = None
    joining_date: date | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    department_id: uuid.UUID | None
    joining_date: date
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
