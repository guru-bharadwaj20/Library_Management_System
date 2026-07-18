"""Application configuration.

Values are read from environment variables (or a local ``.env`` file) via
pydantic-settings, so the same codebase runs unchanged in dev (SQLite) and
production (Postgres) by swapping ``DATABASE_URL`` alone.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "sqlite:///./library.db"

    # Auth
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # CORS
    cors_origins: str = "http://localhost:8501,http://localhost:5173"

    # Domain rules (ported from Python_GUI/codes.py)
    borrow_limit: int = 5
    grace_period_days: int = 2
    base_penalty_rate: float = 1.0
    max_penalty: float = 50.0

    # Initial librarian seed
    admin_username: str = "admin"
    admin_password: str = ""

    # AI features (Claude API). Leave the key blank to disable AI endpoints (they return 503).
    anthropic_api_key: str = ""
    ai_model: str = "claude-opus-4-8"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
