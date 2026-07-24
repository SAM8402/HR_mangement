"""Department listing route.

Provides a single endpoint for retrieving all department names.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.department import Department
from app.models.user import User

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("")
async def list_departments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Department.name).order_by(Department.name))
    names = [row[0] for row in result.all()]
    logger.info("Departments list fetched (%d departments)", len(names))
    return names
