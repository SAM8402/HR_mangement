from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    department_id: uuid.UUID | None
    department: str | None = None
    profile_image: str | None = None

    model_config = {"from_attributes": True}

    @field_validator("department", mode="before")
    @classmethod
    def coerce_department(cls, v):
        if v is not None and not isinstance(v, str):
            return v.name
        return v


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
