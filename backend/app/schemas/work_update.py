from __future__ import annotations

import uuid
import datetime as dt

from pydantic import BaseModel


class WorkUpdateCreate(BaseModel):
    title: str
    description: str
    date: dt.date
    tags: list[str] = []


class WorkUpdateUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    date: dt.date | None = None
    tags: list[str] | None = None


class WorkUpdateResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str
    date: dt.date
    tags: list[str]
    created_at: dt.datetime

    model_config = {"from_attributes": True}
