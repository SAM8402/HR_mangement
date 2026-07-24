from __future__ import annotations

import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def calculate_business_days(from_date: date, to_date: date) -> int:
    """Calculate business days between two dates (inclusive), excluding weekends."""
    if from_date > to_date:
        return 0

    count = 0
    current = from_date
    while current <= to_date:
        # weekday(): Mon=0 ... Sun=6 → exclude 5 (Sat) and 6 (Sun)
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)

    return count
