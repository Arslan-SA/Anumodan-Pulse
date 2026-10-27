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

    # ── JWT Authentication ──────────────────────────────────────────────
    jwt_secret_key: str = "aicte-flowops-development-secret-key-at-least-32-chars-long-2026"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    def validate_production_security(self) -> None:
        """Fail fast if secrets are insecure in production."""
        if self.app_env.lower() == "production":
            if (
                not self.jwt_secret_key
                or "development" in self.jwt_secret_key
                or len(self.jwt_secret_key) < 32
            ):
                raise ValueError(
                    "CRITICAL SECURITY: In production mode, JWT_SECRET_KEY must be a secure random "
                    "string with at least 32 characters."
                )

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so env is read once."""
    return Settings()
