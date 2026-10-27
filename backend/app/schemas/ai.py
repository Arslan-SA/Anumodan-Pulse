"""
AICTE FlowOps — AI Intelligence & Insights Schemas

Typed schemas for AI-assisted executive application summaries,
dashboard pending-work insights, workflow bottleneck diagnostics,
and statutory compliance risks.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


DEFAULT_ADVISORY_DISCLAIMER = (
    "Advisory AI-generated insight. Requires human verification by an "
    "authorized official; does not constitute a statutory or regulatory decision."
)


# ── 1. Application Summary ──────────────────────────────────────────────
class AIApplicationSummaryResponse(BaseModel):
    """Executive summary of an application synthesized from database records."""
    application_id: uuid.UUID
    application_number: str
    institution_id: uuid.UUID
    institution_name: str
    institution_code: Optional[str] = None
    application_type: str
    academic_year: str
    current_stage: Optional[str] = None
    status: str
    submitted_at: Optional[datetime] = None
    days_pending: int = 0
    completed_stages_count: int = 0
    completed_stages: List[str] = Field(default_factory=list)
    outstanding_actions: List[str] = Field(default_factory=list)
    compliance_issues: List[str] = Field(default_factory=list)
    documents_summary: Dict[str, Any] = Field(default_factory=dict)
    executive_summary: str
    key_recommendations: List[str] = Field(default_factory=list)
    is_ai_generated: bool = True
    provider: str = "fallback"
    model: str = "deterministic-rule-engine"
    advisory_disclaimer: str = DEFAULT_ADVISORY_DISCLAIMER

    model_config = ConfigDict(from_attributes=True)


# ── 2. Dashboard Pending-Work Insights ──────────────────────────────────
class InsightItem(BaseModel):
    """An explainable intelligence alert for pending or anomalous work."""
    id: str
    category: str = Field(description="long_pending, multiple_deficiencies, deadline_approaching, expired_documents, bottleneck_stage, attention_required")
    priority: str = Field(description="CRITICAL, HIGH, MEDIUM, LOW")
    title: str
    description: str
    factual_basis: str = Field(description="The exact verifiable backend data that triggered this insight")
    entity_type: str = Field(description="application, compliance, document, workflow_stage")
    entity_id: Optional[str] = None
    reference_number: Optional[str] = None
    recommended_action: str
    timestamp: datetime = Field(default_factory=datetime.now)


class AIDashboardInsightsResponse(BaseModel):
    """Role-scoped high-priority pending-work intelligence items."""
    role: str
    institution_id: Optional[uuid.UUID] = None
    total_insights: int = 0
    high_priority_count: int = 0
    critical_count: int = 0
    items: List[InsightItem] = Field(default_factory=list)
    insights: List[InsightItem] = Field(default_factory=list)
    summary_narrative: str
    is_ai_generated: bool = True
    provider: str = "fallback"
    model: str = "deterministic-rule-engine"
    advisory_disclaimer: str = DEFAULT_ADVISORY_DISCLAIMER



# ── 3. Workflow Bottleneck Analysis ─────────────────────────────────────
class StageBottleneckAnalysis(BaseModel):
    """Bottleneck diagnostic metrics for a specific workflow stage."""
    stage_id: Optional[uuid.UUID] = None
    stage_name: str
    pending_count: int = 0
    average_waiting_days: Optional[float] = None
    target_duration_days: Optional[int] = None
    overdue_count: int = 0
    is_bottleneck: bool = False
    severity: str = "NONE"  # NONE, LOW, MEDIUM, HIGH, CRITICAL
    bottleneck_reasons: List[str] = Field(default_factory=list)
    suggested_mitigations: List[str] = Field(default_factory=list)


class AIWorkflowBottlenecksResponse(BaseModel):
    """Diagnostic analysis of workflow bottlenecks and queue delays."""
    overall_workflow_health: str = Field(description="HEALTHY, MODERATE_DELAY, SEVERE_CONGESTION")
    total_active_applications: int = 0
    bottleneck_stages_count: int = 0
    stages: List[StageBottleneckAnalysis] = Field(default_factory=list)
    narrative_analysis: str
    is_ai_generated: bool = True
    provider: str = "fallback"
    model: str = "deterministic-rule-engine"
    advisory_disclaimer: str = DEFAULT_ADVISORY_DISCLAIMER


# ── 4. Compliance Insights ──────────────────────────────────────────────
class ComplianceRiskItem(BaseModel):
    """An identified compliance undertaking or statutory risk item."""
    id: uuid.UUID
    title: str
    compliance_type: str
    status: str
    due_date: Optional[date] = None
    days_overdue_or_remaining: int = 0
    is_overdue: bool = False
    institution_name: Optional[str] = None
    application_number: Optional[str] = None
    risk_assessment: str


class DocumentExpiryRiskItem(BaseModel):
    """An identified document expiration risk item."""
    id: uuid.UUID
    document_name: str
    document_type: str
    institution_name: Optional[str] = None
    application_number: Optional[str] = None
    expires_at: Optional[datetime] = None
    days_until_expiry: int = 0
    is_expired: bool = False
    risk_assessment: str


class AIComplianceInsightsResponse(BaseModel):
    """Comprehensive compliance and document validity intelligence."""
    total_risk_items: int = 0
    overdue_count: int = 0
    upcoming_deadlines_count: int = 0
    upcoming_count: int = 0
    pending_verification_count: int = 0
    expired_documents_count: int = 0
    expiring_documents_count: int = 0
    overdue_items: List[ComplianceRiskItem] = Field(default_factory=list)
    upcoming_deadlines: List[ComplianceRiskItem] = Field(default_factory=list)
    upcoming_items: List[ComplianceRiskItem] = Field(default_factory=list)
    pending_verification: List[ComplianceRiskItem] = Field(default_factory=list)
    expiring_documents: List[DocumentExpiryRiskItem] = Field(default_factory=list)
    expired_documents: List[DocumentExpiryRiskItem] = Field(default_factory=list)
    common_deficiency_patterns: List[str] = Field(default_factory=list)
    compliance_posture_summary: str
    is_ai_generated: bool = True
    provider: str = "fallback"
    model: str = "deterministic-rule-engine"
    advisory_disclaimer: str = DEFAULT_ADVISORY_DISCLAIMER
