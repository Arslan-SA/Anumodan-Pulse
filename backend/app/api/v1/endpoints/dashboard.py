"""
AICTE FlowOps — Dashboard Analytics Endpoints

Role-specific metrics, workload distributions, ageing analyses,
compliance fulfillments, and alert counters.
"""

from datetime import date
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.dashboard import (
    AlertsAnalyticsResponse,
    ApplicationAnalyticsResponse,
    ComplianceAnalyticsResponse,
    DashboardOverviewResponse,
    WorkflowAnalyticsResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Role-specific dashboard overview",
    description=(
        "Retrieves role-scoped dashboard metrics including application counters, "
        "compliance status, unread alerts, and chronological activity items."
    ),
)
def get_dashboard_overview(
    institution_id: Optional[uuid.UUID] = Query(
        None,
        description="Filter metrics to a specific institution (Admin/Official only).",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DashboardOverviewResponse:
    return DashboardService.get_overview(
        db=db,
        user=current_user,
        institution_id=institution_id,
    )


@router.get(
    "/applications",
    response_model=ApplicationAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Application status and volume analytics",
    description=(
        "Aggregates application status distribution, application types, "
        "academic year totals, and monthly submission time-series trends."
    ),
)
def get_application_analytics(
    start_date: Optional[date] = Query(None, description="Filter applications created on or after date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter applications created on or before date (YYYY-MM-DD)"),
    institution_id: Optional[uuid.UUID] = Query(None, description="Institution filter (Admin/Official only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ApplicationAnalyticsResponse:
    return DashboardService.get_application_analytics(
        db=db,
        user=current_user,
        start_date=start_date,
        end_date=end_date,
        institution_id=institution_id,
    )


@router.get(
    "/workflow",
    response_model=WorkflowAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Workflow load and ageing analytics",
    description=(
        "Computes active application load across workflow stages, ageing duration buckets "
        "(<30d, 30-60d, 60-90d, >90d), average processing duration, and recent transitions."
    ),
)
def get_workflow_analytics(
    institution_id: Optional[uuid.UUID] = Query(None, description="Institution filter (Admin/Official only)"),
    workflow_stage: Optional[str] = Query(None, description="Filter by workflow stage name"),
    start_date: Optional[date] = Query(None, description="Filter on or after date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter on or before date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WorkflowAnalyticsResponse:
    return DashboardService.get_workflow_analytics(
        db=db,
        user=current_user,
        institution_id=institution_id,
        workflow_stage=workflow_stage,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/compliance",
    response_model=ComplianceAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Compliance fulfillment and expiry analytics",
    description=(
        "Aggregates compliance status breakdown, undertaking types, fulfillment percentage, "
        "overdue items, and document validity/expiration buckets."
    ),
)
def get_compliance_analytics(
    institution_id: Optional[uuid.UUID] = Query(None, description="Institution filter (Admin/Official only)"),
    compliance_type: Optional[str] = Query(None, description="Filter by compliance type (e.g., Land, Faculty)"),
    start_date: Optional[date] = Query(None, description="Filter on or after date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter on or before date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ComplianceAnalyticsResponse:
    return DashboardService.get_compliance_analytics(
        db=db,
        user=current_user,
        institution_id=institution_id,
        compliance_type=compliance_type,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/alerts",
    response_model=AlertsAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Notification, alert, and escalation analytics",
    description=(
        "Retrieves notification counts by read status, priority level, notification event type, "
        "recent user alerts, and statutory supervisor escalation histories."
    ),
)
def get_alerts_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AlertsAnalyticsResponse:
    return DashboardService.get_alerts_analytics(
        db=db,
        user=current_user,
    )
