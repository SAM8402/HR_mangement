"""Work update request/response schemas.

Defines Pydantic models for creating, updating, and listing
daily work log entries.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WorkUpdateCreate(BaseModel):
    title: str
    description: str
    date: dt.date
    department: str | None = None
    assigned_user_id: uuid.UUID | None = None
    tags: list[str] = []


class WorkUpdateUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    date: dt.date | None = None
    department: str | None = None
    tags: list[str] | None = None


class WorkUpdateResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str
    date: dt.date
    department: str | None = None
    tags: list[str]
    created_at: dt.datetime

    model_config = {"from_attributes": True}
