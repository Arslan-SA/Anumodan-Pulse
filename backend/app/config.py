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

    # ── Storage Configuration ───────────────────────────────────────────
    storage_backend: str = "local"  # "local" or "s3"
    storage_local_path: str = "./storage/uploads"
    storage_max_file_size_mb: int = 15
    s3_bucket_name: str | None = None
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str | None = None

    # ── Notifications & Scheduler (Phase 7) ─────────────────────────────
    enable_scheduler: bool = True
    scheduler_interval_minutes: int = 15
    default_reminder_windows_days: str = "7,3,1"
    default_escalation_overdue_days: int = 5

    # ── AI Insights & Provider (Phase 9) ────────────────────────────────
    ai_enabled: bool = True
    ai_provider: str = "fallback"  # "fallback", "gemini", "openai", "mock"
    ai_api_key: str | None = None
    ai_model: str = "gemini-1.5-flash"
    ai_temperature: float = 0.2
    ai_timeout_seconds: int = 15
    ai_max_tokens: int = 1500


    def validate_production_security(self) -> None:
        """Fail fast if secrets, database, or cloud storage configuration are insecure in production."""
        if self.app_env.lower() == "production":
            # 1. JWT Secret Key Validation
            if (
                not self.jwt_secret_key
                or "development" in self.jwt_secret_key
                or len(self.jwt_secret_key) < 32
            ):
                raise ValueError(
                    "CRITICAL SECURITY: In production mode, JWT_SECRET_KEY must be a secure random "
                    "string with at least 32 characters."
                )

            # 2. Managed PostgreSQL Validation (Render PostgreSQL)
            db_lower = self.database_url.lower()
            if "sqlite" in db_lower:
                raise ValueError(
                    "CRITICAL DATABASE CONFIGURATION: In production mode, SQLite is forbidden. "
                    "Configure a managed PostgreSQL database via DATABASE_URL."
                )
            if "localhost" in db_lower or "127.0.0.1" in db_lower:
                raise ValueError(
                    "CRITICAL DATABASE CONFIGURATION: In production mode, local database host is forbidden. "
                    "Configure a managed cloud PostgreSQL database (e.g. Render PostgreSQL) via DATABASE_URL."
                )

            # 3. Cloud Object Storage Validation (AWS S3-compatible cloud storage)
            if self.storage_backend.lower() != "s3":
                raise ValueError(
                    "CRITICAL STORAGE CONFIGURATION: In production mode, local filesystem storage is forbidden. "
                    "Set STORAGE_BACKEND=s3 and configure AWS S3-compatible cloud object storage."
                )
            if not self.s3_bucket_name or not self.s3_bucket_name.strip():
                raise ValueError(
                    "CRITICAL STORAGE CONFIGURATION: S3_BUCKET_NAME must be configured in production mode."
                )
            if not self.s3_access_key_id or not self.s3_access_key_id.strip():
                raise ValueError(
                    "CRITICAL STORAGE CONFIGURATION: S3_ACCESS_KEY_ID must be configured in production mode."
                )
            if not self.s3_secret_access_key or not self.s3_secret_access_key.strip():
                raise ValueError(
                    "CRITICAL STORAGE CONFIGURATION: S3_SECRET_ACCESS_KEY must be configured in production mode."
                )

    @property
    def normalized_database_url(self) -> str:
        """Normalize Render/Heroku/AWS postgres:// URLs to SQLAlchemy compatible postgresql://."""
        url = self.database_url
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql://", 1)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def reminder_windows_list(self) -> list[int]:
        """Return parsed reminder window day intervals."""
        try:
            return [int(x.strip()) for x in self.default_reminder_windows_days.split(",") if x.strip()]
        except Exception:
            return [7, 3, 1]



@lru_cache
def get_settings() -> Settings:
    """Cached singleton so env is read once."""
    return Settings()


settings: Settings = get_settings()

