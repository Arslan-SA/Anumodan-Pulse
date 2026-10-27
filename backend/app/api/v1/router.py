"""
AICTE FlowOps — v1 API Router

Aggregates all v1 endpoint routers under a single ``/api/v1`` prefix.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    applications,
    auth,
    compliance,
    compliance_requirements,
    dashboard,
    documents,
    health,
    institutions,
    notifications,
    reminder_rules,
    reports,
    users,
    workflows,
)

router = APIRouter(prefix="/api/v1")

# ── Phase 1 ─────────────────────────────────────────────────────────────
router.include_router(health.router, tags=["Health"])

# ── Phase 3: Auth & User Management ─────────────────────────────────────
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["User Management"])

# ── Phase 4: Institution & Application Management ───────────────────────
router.include_router(institutions.router, prefix="/institutions", tags=["Institutions"])
router.include_router(applications.router, prefix="/applications", tags=["Applications"])

# ── Phase 5: Approval Workflow Engine ───────────────────────────────────
router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])

# ── Phase 6: Compliance, Undertakings, & Document Management ────────────
router.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
router.include_router(
    compliance_requirements.router,
    prefix="/compliance-requirements",
    tags=["Compliance Requirements"],
)
router.include_router(documents.router, prefix="/documents", tags=["Documents"])

# ── Phase 7: Notifications, Alerts, & Escalations ───────────────────────
router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
router.include_router(
    reminder_rules.router,
    prefix="/reminder-rules",
    tags=["Reminder Rules & Escalations"],
)

# ── Phase 8: Dashboard Analytics & Reports ──────────────────────────────
router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(reports.router, prefix="/reports", tags=["Reports"])

# ── Phase 9: AI Insights & Workflow Intelligence ────────────────────────
router.include_router(ai.router, prefix="/ai", tags=["AI Insights & Workflow Intelligence"])

