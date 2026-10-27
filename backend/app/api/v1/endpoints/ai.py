"""
AICTE FlowOps — AI Intelligence & Workflow Insights Endpoints

Provides AI-assisted application summaries, operational pending-work intelligence,
workflow bottleneck diagnostics, and statutory compliance posture insights.

Safety and Decision Boundaries:
- Purely Advisory: AI outputs never approve, reject, or modify application status.
- Strict RBAC: Institution users are restricted to their own institutional data;
  reviewers are restricted to assigned applications.
- Fact-Grounded: Every metric and insight corresponds directly to verified database records.
- Graceful Fallback: Deterministic rule engines provide structured insights if AI is offline.
"""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.ai import (
    AIApplicationSummaryResponse,
    AIComplianceInsightsResponse,
    AIDashboardInsightsResponse,
    AIWorkflowBottlenecksResponse,
)
from app.services.ai_service import AIService

router = APIRouter()


@router.get(
    "/applications/{application_id}/summary",
    response_model=AIApplicationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="AI-assisted application executive briefing",
    description=(
        "Generates an AI-synthesized executive summary and advisory recommendations "
        "for an application based on verified database records. Strictly enforces "
        "institutional data isolation and reviewer assignment restrictions."
    ),
)
def get_application_ai_summary(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AIApplicationSummaryResponse:
    """Return AI executive summary for an application."""
    return AIService.generate_application_summary(
        db=db,
        application_id=application_id,
        user=current_user,
    )


@router.get(
    "/dashboard/insights",
    response_model=AIDashboardInsightsResponse,
    status_code=status.HTTP_200_OK,
    summary="AI-assisted pending-work and operational insights",
    description=(
        "Analyzes ageing applications, multi-item deficiencies, impending compliance "
        "deadlines, and document expiries to provide actionable, prioritized insights."
    ),
)
def get_dashboard_insights(
    institution_id: Optional[uuid.UUID] = Query(
        None,
        description="Filter insights to a specific institution (Admin/Official only).",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AIDashboardInsightsResponse:
    """Return explainable operational intelligence and priority insights."""
    return AIService.generate_dashboard_insights(
        db=db,
        user=current_user,
        institution_id=institution_id,
    )


@router.get(
    "/workflow/bottlenecks",
    response_model=AIWorkflowBottlenecksResponse,
    status_code=status.HTTP_200_OK,
    summary="Workflow queue bottleneck and throughput analysis",
    description=(
        "Diagnoses workflow stages with high pending volumes, prolonged waiting times, "
        "or overdue thresholds, accompanied by advisory load-balancing recommendations."
    ),
)
def get_workflow_bottlenecks(
    institution_id: Optional[uuid.UUID] = Query(
        None,
        description="Filter bottleneck analysis to an institution (Admin/Official only).",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AIWorkflowBottlenecksResponse:
    """Return quantitative bottleneck metrics and advisory operational narrative."""
    return AIService.generate_workflow_bottlenecks(
        db=db,
        user=current_user,
        institution_id=institution_id,
    )


@router.get(
    "/compliance/insights",
    response_model=AIComplianceInsightsResponse,
    status_code=status.HTTP_200_OK,
    summary="Statutory compliance posture and deficiency intelligence",
    description=(
        "Evaluates overdue compliance items, upcoming submission deadlines, items awaiting "
        "official verification, expired or soon-to-expire documents, and common deficiency trends."
    ),
)
def get_compliance_insights(
    institution_id: Optional[uuid.UUID] = Query(
        None,
        description="Filter compliance insights to an institution (Admin/Official only).",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AIComplianceInsightsResponse:
    """Return compliance risk assessment, document expiry alerts, and deficiency trends."""
    return AIService.generate_compliance_insights(
        db=db,
        user=current_user,
        institution_id=institution_id,
    )
