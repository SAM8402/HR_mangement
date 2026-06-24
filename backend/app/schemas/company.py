from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


# ── Company Role ──────────────────────────────────────────────────────────────


class CompanyRoleCreate(BaseModel):
    title: str
    description: str = ""
    responsibilities: str = ""
    required_skills: list[str] = []


class CompanyRoleUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    responsibilities: str | None = None
    required_skills: list[str] | None = None


class CompanyRoleResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    responsibilities: str
    required_skills: list[str]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Company Rule ──────────────────────────────────────────────────────────────


class CompanyRuleCreate(BaseModel):
    title: str
    content: str
    category: str = "general"


class CompanyRuleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None


class CompanyRuleResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    category: str
    created_by: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
