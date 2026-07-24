"""
Application Configuration Module.

Centralizes all configuration settings for the HR Management System.
Loads environment variables from the .env file at the project root
using python-dotenv, then reads them via os.getenv.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

dotenv_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path)

logger = logging.getLogger(__name__)


class Settings:
    """Application settings loaded from environment variables and .env file."""

    APP_NAME: str = os.getenv("APP_NAME", "HR Management System")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    JWT_SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "your-secret-key-change-in-production"
    )
    JWT_ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    LLM_FALLBACK_CHAIN: str = os.getenv("LLM_FALLBACK_CHAIN", "")
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    CORS_ORIGINS: list[str] = json.loads(
        os.getenv("CORS_ORIGINS", '["http://localhost:5173","http://localhost:3000"]')
    )
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "10"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@aura.edu")
    api_keys: list[str] = []

    def __init__(self):
        logger.info("Loaded configuration")
        raw_key = self.GOOGLE_API_KEY
        if raw_key:
            self.api_keys = [k.strip() for k in raw_key.split(",") if k.strip()]
        else:
            self.api_keys = []
        logger.info("Configured %d API key(s)", len(self.api_keys))

        if self.GOOGLE_API_KEY and "," in self.GOOGLE_API_KEY:
            keys = self.api_keys
            for k in keys:
                if k.startswith("AIzaSy"):
                    self.GOOGLE_API_KEY = k
                    break
            else:
                self.GOOGLE_API_KEY = keys[0] if keys else ""

    @property
    def fallback_models(self) -> list[str]:
        if not self.LLM_FALLBACK_CHAIN:
            return []
        return [m.strip() for m in self.LLM_FALLBACK_CHAIN.split(",") if m.strip()]


settings = Settings()
