"""
AICTE FlowOps — Application Configuration

Loads environment variables via pydantic-settings and exposes a single
``Settings`` instance used across the application.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings sourced from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ────────────────────────────────────────────────────────
    database_url: str = "postgresql://postgres:postgres@localhost:5432/aicte_flowops"

    # ── Application ─────────────────────────────────────────────────────
    app_env: str = "development"
    debug: bool = True

    # ── CORS ────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Server ──────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so env is read once."""
    return Settings()
