"""
AICTE FlowOps — v1 API Router

Aggregates all v1 endpoint routers under a single ``/api/v1`` prefix.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, users

router = APIRouter(prefix="/api/v1")

# ── Phase 1 ─────────────────────────────────────────────────────────────
router.include_router(health.router, tags=["Health"])

# ── Phase 3: Auth & User Management ─────────────────────────────────────
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["User Management"])
