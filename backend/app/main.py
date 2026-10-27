"""
AICTE FlowOps — FastAPI Application Factory

Creates and configures the FastAPI application:
- Metadata (title, description, version)
- CORS middleware
- API v1 router
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.v1.router import router as api_v1_router

from app.services.scheduler import start_scheduler, stop_scheduler

from datetime import datetime, timezone
import logging

settings = get_settings()
logger = logging.getLogger("aicte_flowops")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup / shutdown hooks."""
    # Startup validation
    settings.validate_production_security()
    logger.info(f"AICTE FlowOps API starting in {settings.app_env} mode")
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()
    logger.info("AICTE FlowOps API shutting down")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI instance."""
    app = FastAPI(
        title="AICTE FlowOps API",
        description=(
            "Backend API for the AICTE approval workflow automation, "
            "compliance monitoring, and alert management platform."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Root Probes (for Cloud PaaS / Load Balancers) ───────────────
    @app.get("/health", tags=["Health"], summary="Root Liveness Probe")
    def root_health():
        return {
            "status": "healthy",
            "environment": settings.app_env,
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/", tags=["Health"], summary="API Service Index")
    def root_index():
        return {
            "name": "AICTE FlowOps API",
            "status": "active",
            "docs": "/docs",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Routers ─────────────────────────────────────────────────────
    app.include_router(api_v1_router)

    return app


app = create_app()

