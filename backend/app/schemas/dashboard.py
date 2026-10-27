"""
AICTE FlowOps — Dashboard Analytics Schemas

Schemas for role-specific dashboard overviews, application metrics,
workflow ageing, compliance fulfillment, and alert analytics.
"""

from datetime import datetime
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApplicationStatus, ComplianceStatus, NotificationPriority, NotificationType
from app.schemas.escalation import EscalationHistoryResponse
from app.schemas.notification import NotificationResponse


class RecentActivityItem(BaseModel):
    """Unified chronological activity item for dashboards."""
    id: str
    activity_type: str = Field(description="stage_transition, application_submission, compliance_action, escalation")
    application_id: Optional[uuid.UUID] = None
    application_number: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: Optional[str] = None
    timestamp: datetime
    acted_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationSummary(BaseModel):
    """High-level application status counters."""
    total: int = 0
    draft: int = 0
    submitted: int = 0
    under_scrutiny: int = 0
    returned_for_clarification: int = 0
    evc_pending: int = 0
    evc_scheduled: int = 0
    under_review: int = 0
    approved: int = 0
    rejected: int = 0
    closed: int = 0
    requires_action: int = 0


class ComplianceSummary(BaseModel):
    """High-level compliance status counters."""
    total: int = 0
    pending: int = 0
    submitted: int = 0
    under_verification: int = 0
    verified: int = 0
    rejected: int = 0
    overdue: int = 0
    upcoming_deadlines: int = 0
    expiring_documents_30_days: int = 0
    expired_documents: int = 0


class AlertsSummary(BaseModel):
    """High-level alert, reminder, and escalation counters."""
    unread: int = 0
    total: int = 0
    critical: int = 0
    overdue: int = 0
    escalations_count: int = 0


class DashboardOverviewResponse(BaseModel):
    """Unified role-scoped dashboard overview response."""
    role: str
    institution_id: Optional[uuid.UUID] = None
    application_summary: ApplicationSummary
    compliance_summary: ComplianceSummary
    alerts_summary: AlertsSummary
    recent_activity: List[RecentActivityItem] = []


class PeriodCountItem(BaseModel):
    """Time-series aggregation bucket (e.g. YYYY-MM)."""
    period: str
    count: int


class ApplicationAnalyticsResponse(BaseModel):
    """Detailed application analytics breakdown."""
    total_applications: int = 0
    status_distribution: Dict[str, int] = Field(default_factory=dict)
    application_type_distribution: Dict[str, int] = Field(default_factory=dict)
    academic_year_distribution: Dict[str, int] = Field(default_factory=dict)
    submission_trends: List[PeriodCountItem] = Field(default_factory=list)
    approval_rate: float = 0.0


class StageCountItem(BaseModel):
    """Workflow stage load statistics."""
    stage_id: Optional[uuid.UUID] = None
    stage_name: str
    count: int = 0
    average_days_in_stage: Optional[float] = None


class AgeingBuckets(BaseModel):
    """Pending application ageing buckets."""
    under_30_days: int = 0
    days_30_to_60: int = 0
    days_60_to_90: int = 0
    over_90_days: int = 0


class WorkflowAnalyticsResponse(BaseModel):
    """Detailed workflow stage and progression metrics."""
    total_active_in_workflow: int = 0
    stage_distribution: List[StageCountItem] = Field(default_factory=list)
    ageing_buckets: AgeingBuckets
    average_processing_duration_days: Optional[float] = None
    completed_count: int = 0
    recent_transitions: List[RecentActivityItem] = Field(default_factory=list)


class DocumentExpiryBreakdown(BaseModel):
    """Document expiry classification buckets."""
    expired: int = 0
    expiring_7_days: int = 0
    expiring_30_days: int = 0
    expiring_90_days: int = 0
    valid: int = 0


class ComplianceAnalyticsResponse(BaseModel):
    """Detailed compliance and undertaking metrics."""
    total_records: int = 0
    status_breakdown: Dict[str, int] = Field(default_factory=dict)
    type_breakdown: Dict[str, int] = Field(default_factory=dict)
    fulfilment_rate: float = 0.0
    overdue_count: int = 0
    upcoming_deadlines_count: int = 0
    document_expiry_breakdown: DocumentExpiryBreakdown


class AlertsAnalyticsResponse(BaseModel):
    """Detailed alert and notification breakdown."""
    total_notifications: int = 0
    unread_count: int = 0
    read_count: int = 0
    archived_count: int = 0
    priority_breakdown: Dict[str, int] = Field(default_factory=dict)
    type_breakdown: Dict[str, int] = Field(default_factory=dict)
    recent_alerts: List[NotificationResponse] = Field(default_factory=list)
    escalations_count: int = 0
    recent_escalations: List[EscalationHistoryResponse] = Field(default_factory=list)
