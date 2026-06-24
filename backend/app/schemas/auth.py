from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr


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

    model_config = {"from_attributes": True}


class RefreshTokenRequest(BaseModel):
    refresh_token: str
