"""
AICTE FlowOps — AI Intelligence & Workflow Insights Service

Orchestrates AI-assisted executive summaries, dashboard pending-work insights,
workflow bottleneck diagnostics, and statutory compliance intelligence.

Safety & Compliance Rules:
1. Purely advisory: AI outputs NEVER alter application status or make statutory decisions.
2. Verified facts: Every insight references explicit database timestamps and identifiers.
3. Privacy & RBAC: Only authorized institutional data is summarized; sensitive PII is stripped.
4. Resilient Fallback: If external AI is unavailable or fails, deterministic rules handle the request.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy import Date, and_, case, cast, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application
from app.models.compliance import ComplianceRecord
from app.models.document import Document
from app.models.enums import ApplicationStatus, ComplianceStatus, UserRole
from app.models.institution import Institution
from app.models.stage_history import ApplicationStageHistory
from app.models.user import User
from app.models.workflow_stage import WorkflowStage
from app.schemas.ai import (
    AIApplicationSummaryResponse,
    AIComplianceInsightsResponse,
    AIDashboardInsightsResponse,
    AIWorkflowBottlenecksResponse,
    ComplianceRiskItem,
    DEFAULT_ADVISORY_DISCLAIMER,
    DocumentExpiryRiskItem,
    InsightItem,
    StageBottleneckAnalysis,
)
from app.services.ai_provider import AIProviderResult, BaseAIProvider, get_ai_provider
from app.services.application_service import ApplicationService
from app.services.dashboard_service import DashboardService


def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AIService:
    """Service providing AI-assisted summaries, bottleneck analytics, and compliance insights."""

    @staticmethod
    def generate_application_summary(
        db: Session,
        application_id: uuid.UUID,
        user: User,
        ai_provider: Optional[BaseAIProvider] = None,
    ) -> AIApplicationSummaryResponse:
        """
        Synthesizes an executive briefing and advisory recommendations for an application
        strictly based on authorized database records.
        """
        provider = ai_provider or get_ai_provider()

        # 1. Fetch application enforcing institutional and reviewer isolation
        app = ApplicationService.get_application_for_user(db, application_id, user)
        institution = app.institution

        # 2. Extract verified historical facts
        stage_histories = (
            db.scalars(
                select(ApplicationStageHistory)
                .options(joinedload(ApplicationStageHistory.workflow_stage))
                .where(ApplicationStageHistory.application_id == application_id)
                .order_by(ApplicationStageHistory.entered_at)
            )
            .all()
        )

        completed_stages: List[str] = []
        for sh in stage_histories:
            s_name = sh.action_name or (sh.workflow_stage.stage_name if sh.workflow_stage else sh.status)
            if s_name not in completed_stages and sh.exited_at is not None:
                completed_stages.append(s_name)

        # 3. Linked compliance records
        compliance_records = (
            db.scalars(
                select(ComplianceRecord).where(
                    or_(
                        ComplianceRecord.application_id == application_id,
                        and_(
                            ComplianceRecord.institution_id == app.institution_id,
                            ComplianceRecord.status.in_([
                                ComplianceStatus.PENDING,
                                ComplianceStatus.OVERDUE,
                                ComplianceStatus.REJECTED,
                            ]),
                        ),
                    )
                )
            )
            .all()
        )

        today = date.today()
        compliance_issues: List[str] = []
        for c in compliance_records:
            c_status = c.status.value if hasattr(c.status, "value") else str(c.status)
            if c_status in [ComplianceStatus.OVERDUE.value, ComplianceStatus.REJECTED.value]:
                compliance_issues.append(f"{c.title} ({c_status})")
            elif c.due_date and c.due_date < today:
                compliance_issues.append(f"{c.title} (Overdue since {c.due_date})")

        # 4. Uploaded documents
        docs = (
            db.scalars(
                select(Document).where(
                    or_(
                        Document.application_id == application_id,
                        Document.institution_id == app.institution_id,
                    )
                )
            )
            .all()
        )
        total_docs = len(docs)
        now_utc = datetime.now(timezone.utc)
        expiring_docs_count = sum(
            1 for d in docs
            if _normalize_dt(d.expires_at) and now_utc <= _normalize_dt(d.expires_at) <= now_utc + timedelta(days=30)
        )
        expired_docs_count = sum(
            1 for d in docs
            if _normalize_dt(d.expires_at) and _normalize_dt(d.expires_at) < now_utc
        )

        doc_summary: Dict[str, Any] = {
            "total_documents": total_docs,
            "expiring_soon": expiring_docs_count,
            "expiring_soon_count": expiring_docs_count,
            "expired": expired_docs_count,
            "expired_count": expired_docs_count,
            "document_types": list(set(d.document_type for d in docs)),
        }

        # 5. Calculate pending duration
        now_date = today
        ref_date = app.submitted_at.date() if app.submitted_at else app.created_at.date()
        days_pending = max(0, (now_date - ref_date).days)

        # 6. Outstanding actions determination
        outstanding_actions: List[str] = []
        app_status_val = app.status.value if hasattr(app.status, "value") else str(app.status)
        if app_status_val == ApplicationStatus.DRAFT.value:
            outstanding_actions.append("Institution representative must complete mandatory sections and submit application.")
        elif app_status_val == ApplicationStatus.RETURNED_FOR_CLARIFICATION.value:
            outstanding_actions.append("Institution must address official deficiency remarks and resubmit clarification.")
        elif app_status_val == ApplicationStatus.SUBMITTED.value:
            outstanding_actions.append("Regional scrutiny team to commence document scrutiny and verification.")
        elif app_status_val == ApplicationStatus.UNDER_SCRUTINY.value:
            outstanding_actions.append("Scrutiny committee evaluation in progress.")
        elif app_status_val == ApplicationStatus.EVC_PENDING.value:
            outstanding_actions.append("Expert Visit Committee (EVC) panel to be constituted and inspection date scheduled.")
        elif app_status_val == ApplicationStatus.EVC_SCHEDULED.value:
            outstanding_actions.append("Expert Visit Committee to conduct on-site/virtual verification and submit inspection report.")
        elif app_status_val == ApplicationStatus.UNDER_REVIEW.value:
            outstanding_actions.append("Competent approval authority review and statutory determination pending.")
        elif app_status_val in [ApplicationStatus.APPROVED.value, ApplicationStatus.REJECTED.value, ApplicationStatus.CLOSED.value]:
            outstanding_actions.append("Application processing concluded; compliance undertakings monitoring remains active.")

        if compliance_issues:
            outstanding_actions.append(f"Resolve {len(compliance_issues)} identified compliance deficiency items.")
        if expired_docs_count > 0:
            outstanding_actions.append(f"Upload renewed certificates for {expired_docs_count} expired document(s).")

        # 7. Generate Natural Language Executive Briefing
        inst_name = institution.institution_name if institution else "Registered Institution"
        inst_code = institution.institution_code if institution else None
        current_stage_name = app.current_stage or "Intake"

        prompt = (
            f"Synthesize a concise executive summary for approval application:\n"
            f"- Institution: {inst_name} (Code: {inst_code or 'N/A'})\n"
            f"- Application Number: {app.application_number}\n"
            f"- Type: {app.application_type}\n"
            f"- Academic Year: {app.academic_year}\n"
            f"- Current Status: {app_status_val}\n"
            f"- Current Workflow Stage: {current_stage_name}\n"
            f"- Days in Process: {days_pending} days\n"
            f"- Completed Stages: {', '.join(completed_stages) or 'None'}\n"
            f"- Outstanding Actions: {'; '.join(outstanding_actions)}\n"
            f"- Compliance Issues: {'; '.join(compliance_issues) or 'None'}\n"
            f"- Documents: {total_docs} files ({expired_docs_count} expired, {expiring_docs_count} expiring soon)\n\n"
            f"Provide a 2-3 sentence executive briefing highlighting the file's current status and critical blockers. "
            f"Do not recommend approval or rejection."
        )

        sys_prompt = (
            "You are an AI advisor for the AICTE FlowOps approval system. "
            "All recommendations are purely advisory and never make statutory decisions. "
            "Be concise, factual, and professional."
        )

        try:
            res = provider.generate_text(prompt, sys_prompt)
        except Exception as exc:
            res = AIProviderResult(
                content=prompt.strip(),
                provider="fallback",
                model="deterministic-rule-engine",
                is_fallback=True,
                error=str(exc),
            )

        # Build fallback summary if provider returned raw prompt or failed
        if res.is_fallback:
            exec_summary = (
                f"{inst_name} ({inst_code or 'Ref: ' + str(app.institution_id)[:8]}) has applied for "
                f"'{app.application_type}' for academic year {app.academic_year}. The file is currently at the "
                f"'{current_stage_name}' stage with status '{app_status_val}' ({days_pending} days in process). "
                f"Key immediate requirements include: {outstanding_actions[0] if outstanding_actions else 'routine workflow advancement'}."
            )
        else:
            exec_summary = res.content.strip()

        # Key recommendations
        recommendations = [
            f"Verify all {total_docs} uploaded document attachments against current Approval Process Handbook (APH) norms.",
            f"Prioritize resolution of {len(outstanding_actions)} outstanding action item(s) to avoid stage deadline escalation.",
        ]
        if compliance_issues:
            recommendations.append(f"Follow up with institution on {len(compliance_issues)} overdue or rejected compliance undertaking(s).")
        if expired_docs_count > 0:
            recommendations.append(f"Request updated legal certificates for {expired_docs_count} expired document(s).")

        return AIApplicationSummaryResponse(
            application_id=app.id,
            application_number=app.application_number,
            institution_id=app.institution_id,
            institution_name=inst_name,
            institution_code=inst_code,
            application_type=app.application_type,
            academic_year=app.academic_year,
            current_stage=app.current_stage,
            status=app_status_val,
            submitted_at=app.submitted_at,
            days_pending=days_pending,
            completed_stages_count=len(completed_stages),
            completed_stages=completed_stages,
            outstanding_actions=outstanding_actions,
            compliance_issues=compliance_issues,
            documents_summary=doc_summary,
            executive_summary=exec_summary,
            key_recommendations=recommendations,
            is_ai_generated=not res.is_fallback,
            provider=res.provider,
            model=res.model,
            advisory_disclaimer=DEFAULT_ADVISORY_DISCLAIMER,
        )

    @staticmethod
    def generate_dashboard_insights(
        db: Session,
        user: User,
        institution_id: Optional[uuid.UUID] = None,
        ai_provider: Optional[BaseAIProvider] = None,
    ) -> AIDashboardInsightsResponse:
        """
        Generates explainable pending-work intelligence items, bottleneck alerts,
        and advisory notifications for dashboards.
        """
        provider = ai_provider or get_ai_provider()
        scoped_inst_id = DashboardService.check_institution_access(user, institution_id)

        insights: List[InsightItem] = []
        today = date.today()
        now_utc = datetime.now(timezone.utc)

        # ── 1. Long-Pending Applications (> 30 days without final decision) ──
        app_query = select(Application).options(joinedload(Application.institution)).where(
            Application.submitted_at.isnot(None),
            Application.status.in_([
                ApplicationStatus.SUBMITTED,
                ApplicationStatus.UNDER_SCRUTINY,
                ApplicationStatus.RETURNED_FOR_CLARIFICATION,
                ApplicationStatus.EVC_PENDING,
                ApplicationStatus.EVC_SCHEDULED,
                ApplicationStatus.UNDER_REVIEW,
            ]),
            Application.submitted_at <= datetime.now() - timedelta(days=30),
        )
        if scoped_inst_id:
            app_query = app_query.where(Application.institution_id == scoped_inst_id)

        long_pending_apps = db.scalars(app_query.order_by(Application.submitted_at).limit(10)).all()
        for a in long_pending_apps:
            days_wait = (today - a.submitted_at.date()).days if a.submitted_at else 0
            inst_name = a.institution.institution_name if a.institution else "Institution"
            insights.append(
                InsightItem(
                    id=f"insight-app-pending-{a.id}",
                    category="long_pending",
                    priority="HIGH" if days_wait < 60 else "CRITICAL",
                    title=f"Application {a.application_number} Pending for {days_wait} Days",
                    description=(
                        f"Application for '{a.application_type}' by {inst_name} has remained in "
                        f"'{a.current_stage or a.status}' stage for {days_wait} days."
                    ),
                    factual_basis=f"Submitted on {a.submitted_at.strftime('%Y-%m-%d')}, exceeding 30-day target timeline.",
                    entity_type="application",
                    entity_id=str(a.id),
                    reference_number=a.application_number,
                    recommended_action="Expedite pending committee evaluation or issue clarification notice.",
                )
            )

        # ── 2. Applications Requiring Clarification ─────────────────────────
        clarify_query = select(Application).options(joinedload(Application.institution)).where(
            Application.status == ApplicationStatus.RETURNED_FOR_CLARIFICATION
        )
        if scoped_inst_id:
            clarify_query = clarify_query.where(Application.institution_id == scoped_inst_id)

        clarify_apps = db.scalars(clarify_query.limit(10)).all()
        for a in clarify_apps:
            inst_name = a.institution.institution_name if a.institution else "Institution"
            insights.append(
                InsightItem(
                    id=f"insight-clarify-{a.id}",
                    category="multiple_deficiencies",
                    priority="MEDIUM",
                    title=f"Clarification Response Awaited: {a.application_number}",
                    description=f"{inst_name} has not yet submitted clarifications requested during scrutiny review.",
                    factual_basis=f"Status is RETURNED_FOR_CLARIFICATION as of {a.updated_at.strftime('%Y-%m-%d')}.",
                    entity_type="application",
                    entity_id=str(a.id),
                    reference_number=a.application_number,
                    recommended_action="Submit deficiency clarifications with supporting documentation.",
                )
            )

        # ── 3. Overdue & Upcoming Compliance Undertakings ────────────────────
        comp_query = select(ComplianceRecord).options(joinedload(ComplianceRecord.institution)).where(
            or_(
                ComplianceRecord.status == ComplianceStatus.OVERDUE,
                and_(
                    ComplianceRecord.due_date < today,
                    ComplianceRecord.status.in_([
                        ComplianceStatus.PENDING,
                        ComplianceStatus.SUBMITTED,
                        ComplianceStatus.REJECTED,
                    ]),
                ),
            )
        )
        if scoped_inst_id:
            comp_query = comp_query.where(ComplianceRecord.institution_id == scoped_inst_id)

        overdue_records = db.scalars(comp_query.order_by(ComplianceRecord.due_date).limit(10)).all()
        for c in overdue_records:
            inst_name = c.institution.institution_name if c.institution else "Institution"
            days_od = (today - c.due_date).days if c.due_date else 0
            insights.append(
                InsightItem(
                    id=f"insight-comp-od-{c.id}",
                    category="deadline_approaching",
                    priority="HIGH",
                    title=f"Overdue Compliance: {c.title}",
                    description=f"Statutory undertaking '{c.compliance_type}' for {inst_name} is overdue by {days_od} day(s).",
                    factual_basis=f"Due date was {c.due_date.isoformat() if c.due_date else 'N/A'}, current status is {c.status.value if hasattr(c.status, 'value') else c.status}.",
                    entity_type="compliance",
                    entity_id=str(c.id),
                    reference_number=c.title,
                    recommended_action="Submit compliance undertaking and upload verified evidence.",
                )
            )

        # ── 4. Expired and Expiring Documents ───────────────────────────────
        doc_query = select(Document).options(joinedload(Document.institution)).where(
            or_(
                Document.expires_at < now_utc,
                and_(Document.expires_at >= now_utc, Document.expires_at <= now_utc + timedelta(days=30)),
            )
        )
        if scoped_inst_id:
            doc_query = doc_query.where(Document.institution_id == scoped_inst_id)

        exp_docs = db.scalars(doc_query.order_by(Document.expires_at).limit(10)).all()
        for d in exp_docs:
            inst_name = d.institution.institution_name if d.institution else "Institution"
            d_norm = _normalize_dt(d.expires_at)
            is_expired = bool(d_norm and d_norm < now_utc)
            days_diff = abs((today - d_norm.date()).days) if d_norm else 0
            insights.append(
                InsightItem(
                    id=f"insight-doc-exp-{d.id}",
                    category="expired_documents",
                    priority="CRITICAL" if is_expired else "MEDIUM",
                    title=f"{'Expired Document' if is_expired else 'Document Expiring Soon'}: {d.document_name}",
                    description=(
                        f"Document '{d.document_type}' for {inst_name} "
                        f"{'expired ' + str(days_diff) + ' day(s) ago' if is_expired else 'expires in ' + str(days_diff) + ' day(s)'}."
                    ),
                    factual_basis=f"Expiration timestamp recorded as {d.expires_at.strftime('%Y-%m-%d') if d.expires_at else 'N/A'}.",
                    entity_type="document",
                    entity_id=str(d.id),
                    reference_number=d.document_name,
                    recommended_action="Upload renewed sanction letter, land lease, or NOC certificate.",
                )
            )

        # Sort insights by priority (CRITICAL -> HIGH -> MEDIUM -> LOW)
        prio_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        insights.sort(key=lambda x: prio_order.get(x.priority, 4))

        high_priority_cnt = sum(1 for i in insights if i.priority in ["CRITICAL", "HIGH"])

        # Executive summary narrative
        role_label = user.role.value if hasattr(user.role, "value") else str(user.role)
        if insights:
            summary_narrative = (
                f"Generated {len(insights)} operational intelligence insight(s) for {role_label}. "
                f"{high_priority_cnt} require immediate administrative attention, comprising "
                f"{len(long_pending_apps)} delayed application file(s), {len(overdue_records)} overdue compliance item(s), "
                f"and {len(exp_docs)} expiring/expired legal document(s)."
            )
        else:
            summary_narrative = (
                f"All application workflows and statutory compliance items within the current {role_label} "
                f"scope are progressing within configured target timelines. No critical anomalies detected."
            )

        try:
            res_provider = provider.generate_text(
                f"Summarize these workflow insights: {summary_narrative}",
                "You are an AI advisor for AICTE FlowOps. Keep response purely advisory and professional."
            )
        except Exception as exc:
            res_provider = AIProviderResult(
                content=summary_narrative,
                provider="fallback",
                model="deterministic-rule-engine",
                is_fallback=True,
                error=str(exc),
            )

        critical_cnt = sum(1 for i in insights if i.priority == "CRITICAL")

        return AIDashboardInsightsResponse(
            role=role_label,
            institution_id=scoped_inst_id,
            total_insights=len(insights),
            high_priority_count=high_priority_cnt,
            critical_count=critical_cnt,
            items=insights,
            insights=insights,
            summary_narrative=res_provider.content if not res_provider.is_fallback else summary_narrative,
            is_ai_generated=not res_provider.is_fallback,
            provider=res_provider.provider,
            model=res_provider.model,
            advisory_disclaimer=DEFAULT_ADVISORY_DISCLAIMER,
        )

    @staticmethod
    def generate_workflow_bottlenecks(
        db: Session,
        user: User,
        institution_id: Optional[uuid.UUID] = None,
        ai_provider: Optional[BaseAIProvider] = None,
    ) -> AIWorkflowBottlenecksResponse:
        """
        Diagnoses workflow queue delays and identifies bottleneck stages using
        database aggregation against configured stage targets.
        """
        provider = ai_provider or get_ai_provider()
        scoped_inst_id = DashboardService.check_institution_access(user, institution_id)

        # 1. Query active stages with counts
        active_statuses = [
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.UNDER_SCRUTINY,
            ApplicationStatus.RETURNED_FOR_CLARIFICATION,
            ApplicationStatus.EVC_PENDING,
            ApplicationStatus.EVC_SCHEDULED,
            ApplicationStatus.UNDER_REVIEW,
        ]
        filters = [Application.status.in_(active_statuses)]
        if scoped_inst_id:
            filters.append(Application.institution_id == scoped_inst_id)

        total_active = db.scalar(select(func.count(Application.id)).where(*filters)) or 0

        # Query stage group counts
        stage_group_query = (
            select(
                Application.current_stage,
                Application.current_stage_id,
                func.count(Application.id).label("pending_count"),
                func.avg(
                    func.extract("epoch", func.now() - Application.submitted_at) / 86400
                ).label("avg_waiting_days"),
            )
            .where(*filters, Application.submitted_at.isnot(None))
            .group_by(Application.current_stage, Application.current_stage_id)
        )
        stage_rows = db.execute(stage_group_query).all()

        stages_analysis: List[StageBottleneckAnalysis] = []
        bottleneck_count = 0

        # Standard configurable default target for stages (e.g. 15-30 days)
        DEFAULT_STAGE_TARGET = 21

        for row in stage_rows:
            stage_name = row.current_stage or "Unassigned Stage"
            pending_cnt = row.pending_count or 0
            avg_wait = round(float(row.avg_waiting_days), 1) if row.avg_waiting_days is not None else None

            # Calculate overdue count for this stage
            overdue_in_stage_query = select(func.count(Application.id)).where(
                *filters,
                Application.current_stage == row.current_stage,
                Application.submitted_at.isnot(None),
                Application.submitted_at <= datetime.now() - timedelta(days=DEFAULT_STAGE_TARGET),
            )
            overdue_cnt = db.scalar(overdue_in_stage_query) or 0

            # Determine bottleneck severity
            is_bottleneck = False
            severity = "NONE"
            reasons = []
            mitigations = []

            if pending_cnt >= 5 or (avg_wait and avg_wait > DEFAULT_STAGE_TARGET):
                is_bottleneck = True
                bottleneck_count += 1
                if overdue_cnt > 3 or (avg_wait and avg_wait > DEFAULT_STAGE_TARGET * 1.5):
                    severity = "CRITICAL"
                    reasons.append(f"High queue delay: average turnaround is {avg_wait} days, exceeding {DEFAULT_STAGE_TARGET}-day target.")
                    reasons.append(f"{overdue_cnt} applications currently breach stage target timeline.")
                    mitigations.append("Deploy additional scrutiny officers or schedule emergency evaluation sessions.")
                    mitigations.append("Reassign eligible pending files to parallel regional review desks.")
                else:
                    severity = "HIGH" if pending_cnt >= 3 else "MEDIUM"
                    reasons.append(f"{pending_cnt} application files awaiting processing in this stage.")
                    mitigations.append("Monitor file movement daily and trigger advisory reminder notifications.")

            stages_analysis.append(
                StageBottleneckAnalysis(
                    stage_id=row.current_stage_id,
                    stage_name=stage_name,
                    pending_count=pending_cnt,
                    average_waiting_days=avg_wait,
                    target_duration_days=DEFAULT_STAGE_TARGET,
                    overdue_count=overdue_cnt,
                    is_bottleneck=is_bottleneck,
                    severity=severity,
                    bottleneck_reasons=reasons,
                    suggested_mitigations=mitigations,
                )
            )

        # Overall health assessment
        if bottleneck_count >= 2 or any(s.severity == "CRITICAL" for s in stages_analysis):
            overall_health = "SEVERE_CONGESTION"
        elif bottleneck_count == 1:
            overall_health = "MODERATE_DELAY"
        else:
            overall_health = "HEALTHY"

        # AI narrative synthesis
        prompt = (
            f"Provide a 2-3 sentence diagnostic analysis of AICTE workflow queues:\n"
            f"- Total Active Applications: {total_active}\n"
            f"- Bottleneck Stages Count: {bottleneck_count}\n"
            f"- Overall System Health: {overall_health}\n"
            f"- Stages: {[s.stage_name + ' (pending: ' + str(s.pending_count) + ', avg wait: ' + str(s.average_waiting_days) + 'd)' for s in stages_analysis]}\n"
            f"Explain where delays are concentrated and suggest operational load-balancing measures. Purely advisory."
        )
        try:
            res_provider = provider.generate_text(
                prompt,
                "You are an AI advisor analyzing workflow throughput. Keep response purely advisory and professional."
            )
        except Exception as exc:
            res_provider = AIProviderResult(
                content=prompt,
                provider="fallback",
                model="deterministic-rule-engine",
                is_fallback=True,
                error=str(exc),
            )

        if res_provider.is_fallback:
            if bottleneck_count > 0:
                top_bn = next((s for s in stages_analysis if s.is_bottleneck), stages_analysis[0] if stages_analysis else None)
                narrative = (
                    f"Workflow queue analysis identified {bottleneck_count} bottleneck stage(s). "
                    f"Concentration is highest in '{top_bn.stage_name if top_bn else 'Review'}' "
                    f"with {top_bn.pending_count if top_bn else 0} pending file(s) and an average turnaround of "
                    f"{top_bn.average_waiting_days if top_bn else 0} days. Administrative load-balancing is recommended."
                )
            else:
                narrative = (
                    f"Workflow throughput is currently optimal across all stages with {total_active} active "
                    f"application(s). Processing times remain within configured target timelines."
                )
        else:
            narrative = res_provider.content.strip()

        return AIWorkflowBottlenecksResponse(
            overall_workflow_health=overall_health,
            total_active_applications=total_active,
            bottleneck_stages_count=bottleneck_count,
            stages=stages_analysis,
            narrative_analysis=narrative,
            is_ai_generated=not res_provider.is_fallback,
            provider=res_provider.provider,
            model=res_provider.model,
            advisory_disclaimer=DEFAULT_ADVISORY_DISCLAIMER,
        )

    @staticmethod
    def generate_compliance_insights(
        db: Session,
        user: User,
        institution_id: Optional[uuid.UUID] = None,
        ai_provider: Optional[BaseAIProvider] = None,
    ) -> AIComplianceInsightsResponse:
        """
        Synthesizes compliance posture intelligence, identified deficiency patterns,
        and impending document expiration risks.
        """
        provider = ai_provider or get_ai_provider()
        scoped_inst_id = DashboardService.check_institution_access(user, institution_id)

        today = date.today()
        now_utc = datetime.now(timezone.utc)

        # 1. Overdue compliance items
        overdue_filters = [
            or_(
                ComplianceRecord.status == ComplianceStatus.OVERDUE,
                and_(
                    ComplianceRecord.due_date < today,
                    ComplianceRecord.status.in_([
                        ComplianceStatus.PENDING,
                        ComplianceStatus.SUBMITTED,
                        ComplianceStatus.REJECTED,
                    ]),
                ),
            )
        ]
        if scoped_inst_id:
            overdue_filters.append(ComplianceRecord.institution_id == scoped_inst_id)

        overdue_records = (
            db.scalars(
                select(ComplianceRecord)
                .options(joinedload(ComplianceRecord.institution), joinedload(ComplianceRecord.application))
                .where(*overdue_filters)
                .order_by(ComplianceRecord.due_date)
                .limit(20)
            )
            .all()
        )
        overdue_items = [
            ComplianceRiskItem(
                id=c.id,
                title=c.title,
                compliance_type=c.compliance_type,
                status=c.status.value if hasattr(c.status, "value") else str(c.status),
                due_date=c.due_date,
                days_overdue_or_remaining=max(0, (today - c.due_date).days) if c.due_date else 0,
                is_overdue=True,
                institution_name=c.institution.institution_name if c.institution else None,
                application_number=c.application.application_number if c.application else None,
                risk_assessment="High statutory risk: Undertaking elapsed without authorized verification.",
            )
            for c in overdue_records
        ]

        # 2. Upcoming deadlines (within 14 days)
        upcoming_filters = [
            ComplianceRecord.due_date >= today,
            ComplianceRecord.due_date <= today + timedelta(days=14),
            ComplianceRecord.status.in_([
                ComplianceStatus.PENDING,
                ComplianceStatus.SUBMITTED,
                ComplianceStatus.UNDER_VERIFICATION,
            ]),
        ]
        if scoped_inst_id:
            upcoming_filters.append(ComplianceRecord.institution_id == scoped_inst_id)

        upcoming_records = (
            db.scalars(
                select(ComplianceRecord)
                .options(joinedload(ComplianceRecord.institution), joinedload(ComplianceRecord.application))
                .where(*upcoming_filters)
                .order_by(ComplianceRecord.due_date)
                .limit(20)
            )
            .all()
        )
        upcoming_items = [
            ComplianceRiskItem(
                id=c.id,
                title=c.title,
                compliance_type=c.compliance_type,
                status=c.status.value if hasattr(c.status, "value") else str(c.status),
                due_date=c.due_date,
                days_overdue_or_remaining=max(0, (c.due_date - today).days) if c.due_date else 0,
                is_overdue=False,
                institution_name=c.institution.institution_name if c.institution else None,
                application_number=c.application.application_number if c.application else None,
                risk_assessment=f"Due in {(c.due_date - today).days if c.due_date else 0} days: Evidence submission required.",
            )
            for c in upcoming_records
        ]

        # 3. Pending verification
        verif_filters = [ComplianceRecord.status.in_([ComplianceStatus.SUBMITTED, ComplianceStatus.UNDER_VERIFICATION])]
        if scoped_inst_id:
            verif_filters.append(ComplianceRecord.institution_id == scoped_inst_id)

        verif_records = (
            db.scalars(
                select(ComplianceRecord)
                .options(joinedload(ComplianceRecord.institution), joinedload(ComplianceRecord.application))
                .where(*verif_filters)
                .limit(20)
            )
            .all()
        )
        pending_verif_items = [
            ComplianceRiskItem(
                id=c.id,
                title=c.title,
                compliance_type=c.compliance_type,
                status=c.status.value if hasattr(c.status, "value") else str(c.status),
                due_date=c.due_date,
                days_overdue_or_remaining=0,
                is_overdue=False,
                institution_name=c.institution.institution_name if c.institution else None,
                application_number=c.application.application_number if c.application else None,
                risk_assessment="Evidence uploaded: Awaiting scrutiny verification by authorized official.",
            )
            for c in verif_records
        ]

        # 4. Expiring / Expired Documents
        doc_filters = [
            or_(
                Document.expires_at < now_utc,
                and_(Document.expires_at >= now_utc, Document.expires_at <= now_utc + timedelta(days=30)),
            )
        ]
        if scoped_inst_id:
            doc_filters.append(Document.institution_id == scoped_inst_id)

        doc_records = (
            db.scalars(
                select(Document)
                .options(joinedload(Document.institution), joinedload(Document.application))
                .where(*doc_filters)
                .order_by(Document.expires_at)
                .limit(20)
            )
            .all()
        )
        expiring_docs_items: List[DocumentExpiryRiskItem] = []
        expired_count = 0
        expiring_count = 0

        for d in doc_records:
            d_norm = _normalize_dt(d.expires_at)
            is_expired = bool(d_norm and d_norm < now_utc)
            if is_expired:
                expired_count += 1
                days_val = (today - d_norm.date()).days if d_norm else 0
                risk_str = f"Expired {days_val} day(s) ago: Institutional clearance invalid."
            else:
                expiring_count += 1
                days_val = (d_norm.date() - today).days if d_norm else 0
                risk_str = f"Impending expiration in {days_val} day(s): Renewal required."

            expiring_docs_items.append(
                DocumentExpiryRiskItem(
                    id=d.id,
                    document_name=d.document_name,
                    document_type=d.document_type,
                    institution_name=d.institution.institution_name if d.institution else None,
                    application_number=d.application.application_number if d.application else None,
                    expires_at=d.expires_at,
                    days_until_expiry=days_val,
                    is_expired=is_expired,
                    risk_assessment=risk_str,
                )
            )

        # 5. Common deficiency patterns
        type_count_query = (
            select(ComplianceRecord.compliance_type, func.count(ComplianceRecord.id))
            .where(*overdue_filters)
            .group_by(ComplianceRecord.compliance_type)
        )
        common_patterns = [
            f"Frequent overdue filings in '{comp_t}' ({cnt} incident(s))"
            for comp_t, cnt in db.execute(type_count_query).all()
        ]

        total_risks = len(overdue_items) + len(upcoming_items) + len(expiring_docs_items)

        # 6. Posture summary
        if total_risks > 0:
            summary = (
                f"Statutory compliance review identified {len(overdue_items)} overdue undertaking(s), "
                f"{len(upcoming_items)} upcoming deadline(s) within 14 days, and {len(expiring_docs_items)} "
                f"expired/expiring document(s). Active monitoring is required to maintain regulatory compliance."
            )
        else:
            summary = "Institutional compliance posture is healthy. No overdue statutory undertakings or expired certificates."

        try:
            res_provider = provider.generate_text(
                f"Summarize compliance risks: {summary}",
                "You are an AI advisor for statutory compliance. Keep outputs purely advisory and factual."
            )
        except Exception as exc:
            res_provider = AIProviderResult(
                content=summary,
                provider="fallback",
                model="deterministic-rule-engine",
                is_fallback=True,
                error=str(exc),
            )

        return AIComplianceInsightsResponse(
            total_risk_items=total_risks,
            overdue_count=len(overdue_items),
            upcoming_deadlines_count=len(upcoming_items),
            upcoming_count=len(upcoming_items),
            pending_verification_count=len(pending_verif_items),
            expired_documents_count=expired_count,
            expiring_documents_count=expiring_count,
            overdue_items=overdue_items,
            upcoming_deadlines=upcoming_items,
            upcoming_items=upcoming_items,
            pending_verification=pending_verif_items,
            expiring_documents=expiring_docs_items,
            expired_documents=[d for d in expiring_docs_items if d.is_expired],
            common_deficiency_patterns=common_patterns,
            compliance_posture_summary=res_provider.content if not res_provider.is_fallback else summary,
            is_ai_generated=not res_provider.is_fallback,
            provider=res_provider.provider,
            model=res_provider.model,
            advisory_disclaimer=DEFAULT_ADVISORY_DISCLAIMER,
        )
