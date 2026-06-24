"""
Application Configuration Module.

Centralizes all configuration settings for the HR Management System.
Uses Pydantic Settings for type-safe environment variable loading
and validation with sensible defaults.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""
    APP_NAME: str = "HR Management System"
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/hr_db"
    )
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    LLM_FALLBACK_CHAIN: str = ""
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    api_keys: list[str] = []

    @property
    def fallback_models(self) -> list[str]:
        if not self.LLM_FALLBACK_CHAIN:
            return []
        return [m.strip() for m in self.LLM_FALLBACK_CHAIN.split(",") if m.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}

    def __init__(self, **values):
        super().__init__(**values)
        raw_key = self.GOOGLE_API_KEY
        if raw_key:
            self.api_keys = [k.strip() for k in raw_key.split(",") if k.strip()]
        else:
            self.api_keys = []
            
        if self.GOOGLE_API_KEY and "," in self.GOOGLE_API_KEY:
            keys = self.api_keys
            for k in keys:
                if k.startswith("AIzaSy"):
                    self.GOOGLE_API_KEY = k
                    break
            else:
                self.GOOGLE_API_KEY = keys[0] if keys else ""


settings = Settings()
