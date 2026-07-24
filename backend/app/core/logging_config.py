"""
Logging configuration module.

Sets up rotating file and console logging for the entire application.
Import this module at application startup to activate logging.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"


def setup_logging(
    level: int = logging.INFO,
    log_file: str | Path = LOG_FILE,
    max_bytes: int = 5_242_880,
    backup_count: int = 3,
) -> None:
    """Configure root logger with rotating file handler and console handler."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.getLogger("passlib").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.WARNING)


setup_logging()
