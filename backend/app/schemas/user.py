from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, field_validator


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
    profile_image: str | None = None


class UserProfileImageUpdate(BaseModel):
    profile_image: str


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    department_id: uuid.UUID | None
    department: str | None = None
    joining_date: date
    is_active: bool
    profile_image: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("department", mode="before")
    @classmethod
    def coerce_department(cls, v):
        if v is not None and not isinstance(v, str):
            return v.name
        return v


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
