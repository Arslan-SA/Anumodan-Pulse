"""
AICTE FlowOps — Health Check Endpoint

GET /api/v1/health → returns API status, environment, and version.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()

settings = get_settings()


@router.get("/health")
def health_check():
    """Lightweight liveness / readiness probe."""
    return {
        "status": "healthy",
        "environment": settings.app_env,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
