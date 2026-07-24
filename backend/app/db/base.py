"""
SQLAlchemy Declarative Base.

All ORM models inherit from this base class.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass
