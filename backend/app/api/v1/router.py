"""
AICTE FlowOps — v1 API Router

Aggregates all v1 endpoint routers under a single ``/api/v1`` prefix.
New feature routers (auth, applications, workflows, …) will be included
here in later phases.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health

router = APIRouter(prefix="/api/v1")

# ── Phase 1 ─────────────────────────────────────────────────────────────
router.include_router(health.router, tags=["Health"])
