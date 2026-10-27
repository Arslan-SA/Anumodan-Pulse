"""
AICTE FlowOps — Dashboard Analytics Service

Provides high-performance database-level aggregations and role-tailored analytics
for Institution Representatives, AICTE Officials, System Administrators, and Reviewers.
Strictly isolates institutional data and ensures zero hardcoded sample values.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy import (
    Date,
    and_,
    case,
    cast,
    desc,
    func,
    or_,
    select,
)
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application
from app.models.compliance import ComplianceRecord
from app.models.document import Document
from app.models.enums import (
    ApplicationStatus,
    ComplianceStatus,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
    UserRole,
)
from app.models.escalation_history import EscalationHistory
from app.models.notification import Notification
from app.models.stage_history import ApplicationStageHistory
from app.models.user import User
from app.models.workflow_stage import WorkflowStage
from app.schemas.dashboard import (
    AgeingBuckets,
    AlertsAnalyticsResponse,
    AlertsSummary,
    ApplicationAnalyticsResponse,
    ApplicationSummary,
    ComplianceAnalyticsResponse,
    ComplianceSummary,
    DashboardOverviewResponse,
    DocumentExpiryBreakdown,
    PeriodCountItem,
    RecentActivityItem,
    StageCountItem,
    WorkflowAnalyticsResponse,
)
from app.schemas.escalation import EscalationHistoryResponse
from app.schemas.notification import NotificationResponse


class DashboardService:
    """Service providing role-based dashboard aggregations and analytics metrics."""

    @staticmethod
    def check_institution_access(
        user: User,
        institution_id: Optional[uuid.UUID] = None,
    ) -> Optional[uuid.UUID]:
        """
        Validates institution access permissions.
        - Institution users can ONLY access their own institution.
        - Admin and Officials can query all or filter by a specific institution.
        - Reviewers cannot query by institution ID.
        """
        if user.role == UserRole.INSTITUTION_USER:
            if not user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User account is not linked to any registered institution.",
                )
            if institution_id and institution_id != user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Institution users are not permitted to access another institution's data.",
                )
            return user.institution_id

        if user.role == UserRole.REVIEWER:
            if institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Reviewers are not permitted to filter by institution ID.",
                )
            return None

        # Admin and AICTE Official
        return institution_id

    @staticmethod
    def get_overview(
        db: Session,
        user: User,
        institution_id: Optional[uuid.UUID] = None,
    ) -> DashboardOverviewResponse:
        """
        Returns high-level summary counters and recent activities tailored to the user's role.
        """
        scoped_inst_id = DashboardService.check_institution_access(user, institution_id)

        # ── Reviewer Role ───────────────────────────────────────────────────
        if user.role == UserRole.REVIEWER:
            # Reviewers only see assigned reviews; unassigned returns safe empty metrics
            alerts_stmt = (
                select(Notification.status, func.count(Notification.id))
                .where(Notification.recipient_user_id == user.id)
                .group_by(Notification.status)
            )
            alerts_res = dict(db.execute(alerts_stmt).all())
            unread_alerts = alerts_res.get(NotificationStatus.UNREAD, 0)
            total_alerts = sum(alerts_res.values())

            role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
            return DashboardOverviewResponse(
                role=role_val,
                institution_id=None,
                application_summary=ApplicationSummary(),
                compliance_summary=ComplianceSummary(),
                alerts_summary=AlertsSummary(
                    unread=unread_alerts,
                    total=total_alerts,
                    critical=0,
                    overdue=0,
                    escalations_count=0,
                ),
                recent_activity=[],
            )

        # ── 1. Application Summary ──────────────────────────────────────────
        app_where = []
        if scoped_inst_id:
            app_where.append(Application.institution_id == scoped_inst_id)

        app_status_query = (
            select(Application.status, func.count(Application.id))
            .where(*app_where)
            .group_by(Application.status)
        )
        app_counts = dict(db.execute(app_status_query).all())

        total_apps = sum(app_counts.values())
        draft_apps = app_counts.get(ApplicationStatus.DRAFT, 0)
        submitted_apps = app_counts.get(ApplicationStatus.SUBMITTED, 0)
        under_scrutiny_apps = app_counts.get(ApplicationStatus.UNDER_SCRUTINY, 0)
        returned_apps = app_counts.get(ApplicationStatus.RETURNED_FOR_CLARIFICATION, 0)
        evc_pending_apps = app_counts.get(ApplicationStatus.EVC_PENDING, 0)
        evc_scheduled_apps = app_counts.get(ApplicationStatus.EVC_SCHEDULED, 0)
        under_review_apps = app_counts.get(ApplicationStatus.UNDER_REVIEW, 0)
        approved_apps = app_counts.get(ApplicationStatus.APPROVED, 0)
        rejected_apps = app_counts.get(ApplicationStatus.REJECTED, 0)
        closed_apps = app_counts.get(ApplicationStatus.CLOSED, 0)

        if user.role == UserRole.INSTITUTION_USER:
            # Action required for institution = Returned for Clarification
            requires_action = returned_apps
        else:
            # Awaiting official action = Submitted, Under Scrutiny, EVC Pending, Under Review
            requires_action = submitted_apps + under_scrutiny_apps + evc_pending_apps + under_review_apps

        app_summary = ApplicationSummary(
            total=total_apps,
            draft=draft_apps,
            submitted=submitted_apps,
            under_scrutiny=under_scrutiny_apps,
            returned_for_clarification=returned_apps,
            evc_pending=evc_pending_apps,
            evc_scheduled=evc_scheduled_apps,
            under_review=under_review_apps,
            approved=approved_apps,
            rejected=rejected_apps,
            closed=closed_apps,
            requires_action=requires_action,
        )

        # ── 2. Compliance Summary ───────────────────────────────────────────
        comp_where = []
        if scoped_inst_id:
            comp_where.append(ComplianceRecord.institution_id == scoped_inst_id)

        comp_status_query = (
            select(ComplianceRecord.status, func.count(ComplianceRecord.id))
            .where(*comp_where)
            .group_by(ComplianceRecord.status)
        )
        comp_counts = dict(db.execute(comp_status_query).all())

        total_comp = sum(comp_counts.values())
        pending_comp = comp_counts.get(ComplianceStatus.PENDING, 0)
        submitted_comp = comp_counts.get(ComplianceStatus.SUBMITTED, 0)
        under_verification_comp = comp_counts.get(ComplianceStatus.UNDER_VERIFICATION, 0)
        verified_comp = comp_counts.get(ComplianceStatus.VERIFIED, 0)
        rejected_comp = comp_counts.get(ComplianceStatus.REJECTED, 0)

        # Overdue compliance: explicit OVERDUE status OR (due_date in past AND not verified/closed)
        today = date.today()
        overdue_comp_query = (
            select(func.count(ComplianceRecord.id))
            .where(
                *comp_where,
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
                ),
            )
        )
        overdue_comp = db.scalar(overdue_comp_query) or 0

        # Upcoming compliance deadlines within 14 days
        upcoming_window = today + timedelta(days=14)
        upcoming_comp_query = (
            select(func.count(ComplianceRecord.id))
            .where(
                *comp_where,
                ComplianceRecord.due_date >= today,
                ComplianceRecord.due_date <= upcoming_window,
                ComplianceRecord.status.in_([
                    ComplianceStatus.PENDING,
                    ComplianceStatus.SUBMITTED,
                    ComplianceStatus.UNDER_VERIFICATION,
                ]),
            )
        )
        upcoming_comp = db.scalar(upcoming_comp_query) or 0

        # Document expiry counts
        doc_where = []
        if scoped_inst_id:
            doc_where.append(Document.institution_id == scoped_inst_id)

        now = datetime.now()
        doc_exp_30_query = (
            select(func.count(Document.id))
            .where(
                *doc_where,
                Document.expires_at >= now,
                Document.expires_at <= now + timedelta(days=30),
            )
        )
        expiring_30_docs = db.scalar(doc_exp_30_query) or 0

        doc_expired_query = (
            select(func.count(Document.id))
            .where(
                *doc_where,
                Document.expires_at < now,
            )
        )
        expired_docs = db.scalar(doc_expired_query) or 0

        compliance_summary = ComplianceSummary(
            total=total_comp,
            pending=pending_comp,
            submitted=submitted_comp,
            under_verification=under_verification_comp,
            verified=verified_comp,
            rejected=rejected_comp,
            overdue=overdue_comp,
            upcoming_deadlines=upcoming_comp,
            expiring_documents_30_days=expiring_30_docs,
            expired_documents=expired_docs,
        )

        # ── 3. Alerts Summary ───────────────────────────────────────────────
        alert_where = []
        if user.role == UserRole.INSTITUTION_USER:
            alert_where.append(Notification.recipient_user_id == user.id)
            escalations_count = 0
        else:
            escalations_count = db.scalar(select(func.count(EscalationHistory.id))) or 0

        alert_status_query = (
            select(
                Notification.status,
                func.count(Notification.id),
            )
            .where(*alert_where)
            .group_by(Notification.status)
        )
        alert_counts = dict(db.execute(alert_status_query).all())
        unread_alerts = alert_counts.get(NotificationStatus.UNREAD, 0)
        total_alerts = sum(alert_counts.values())

        critical_alerts_query = (
            select(func.count(Notification.id))
            .where(
                *alert_where,
                Notification.priority == NotificationPriority.CRITICAL,
            )
        )
        critical_alerts = db.scalar(critical_alerts_query) or 0

        overdue_alerts_query = (
            select(func.count(Notification.id))
            .where(
                *alert_where,
                Notification.notification_type.in_([
                    NotificationType.COMPLIANCE_OVERDUE,
                    NotificationType.DOCUMENT_EXPIRED,
                ]),
            )
        )
        overdue_alerts = db.scalar(overdue_alerts_query) or 0

        alerts_summary = AlertsSummary(
            unread=unread_alerts,
            total=total_alerts,
            critical=critical_alerts,
            overdue=overdue_alerts,
            escalations_count=escalations_count,
        )

        # ── 4. Recent Activity ──────────────────────────────────────────────
        recent_activity_query = (
            select(ApplicationStageHistory)
            .join(Application, ApplicationStageHistory.application_id == Application.id)
            .options(
                joinedload(ApplicationStageHistory.application),
                joinedload(ApplicationStageHistory.acted_by_user),
            )
            .order_by(desc(ApplicationStageHistory.entered_at))
            .limit(10)
        )
        if scoped_inst_id:
            recent_activity_query = recent_activity_query.where(
                Application.institution_id == scoped_inst_id
            )

        stage_histories = db.scalars(recent_activity_query).all()
        recent_activities: List[RecentActivityItem] = []
        for sh in stage_histories:
            recent_activities.append(
                RecentActivityItem(
                    id=str(sh.id),
                    activity_type="stage_transition",
                    application_id=sh.application_id,
                    application_number=sh.application.application_number if sh.application else None,
                    title=f"Stage transition: {sh.action_name or sh.status}",
                    description=sh.remarks,
                    status=sh.status,
                    timestamp=sh.entered_at,
                    acted_by=sh.acted_by_user.full_name if sh.acted_by_user else None,
                )
            )

        role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
        return DashboardOverviewResponse(
            role=role_val,
            institution_id=scoped_inst_id,
            application_summary=app_summary,
            compliance_summary=compliance_summary,
            alerts_summary=alerts_summary,
            recent_activity=recent_activities,
        )

    @staticmethod
    def get_application_analytics(
        db: Session,
        user: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        institution_id: Optional[uuid.UUID] = None,
    ) -> ApplicationAnalyticsResponse:
        """
        Calculates status distributions, application type breakdowns, academic year counts,
        and submission time-series trends using database aggregations.
        """
        scoped_inst_id = DashboardService.check_institution_access(user, institution_id)

        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be later than end_date.",
            )

        filters = []
        if scoped_inst_id:
            filters.append(Application.institution_id == scoped_inst_id)
        if start_date:
            filters.append(cast(Application.created_at, Date) >= start_date)
        if end_date:
            filters.append(cast(Application.created_at, Date) <= end_date)

        # 1. Status Distribution
        status_query = (
            select(Application.status, func.count(Application.id))
            .where(*filters)
            .group_by(Application.status)
        )
        status_distribution = {
            (k.value if hasattr(k, "value") else str(k)): v
            for k, v in db.execute(status_query).all()
        }
        total_apps = sum(status_distribution.values())

        # 2. Application Type Distribution
        type_query = (
            select(Application.application_type, func.count(Application.id))
            .where(*filters)
            .group_by(Application.application_type)
        )
        type_distribution = dict(db.execute(type_query).all())

        # 3. Academic Year Distribution
        year_query = (
            select(Application.academic_year, func.count(Application.id))
            .where(*filters)
            .group_by(Application.academic_year)
        )
        year_distribution = dict(db.execute(year_query).all())

        # 4. Submission Trends (grouped by Year-Month)
        trend_filters = [*filters, Application.submitted_at.isnot(None)]
        trend_query = (
            select(
                func.to_char(Application.submitted_at, "YYYY-MM").label("period"),
                func.count(Application.id).label("count"),
            )
            .where(*trend_filters)
            .group_by("period")
            .order_by("period")
        )
        trends = [
            PeriodCountItem(period=str(period), count=count)
            for period, count in db.execute(trend_query).all()
        ]

        # 5. Approval rate: approved / (approved + rejected + closed)
        approved = status_distribution.get(ApplicationStatus.APPROVED.value, 0)
        rejected = status_distribution.get(ApplicationStatus.REJECTED.value, 0)
        closed = status_distribution.get(ApplicationStatus.CLOSED.value, 0)
        decided_total = approved + rejected + closed
        approval_rate = round((approved / decided_total * 100), 2) if decided_total > 0 else 0.0

        return ApplicationAnalyticsResponse(
            total_applications=total_apps,
            status_distribution=status_distribution,
            application_type_distribution=type_distribution,
            academic_year_distribution=year_distribution,
            submission_trends=trends,
            approval_rate=approval_rate,
        )

    @staticmethod
    def get_workflow_analytics(
        db: Session,
        user: User,
        institution_id: Optional[uuid.UUID] = None,
        workflow_stage: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> WorkflowAnalyticsResponse:
        """
        Calculates workflow stage load, pending application ageing buckets, average processing
        duration for completed applications, and recent transition logs.
        """
        scoped_inst_id = DashboardService.check_institution_access(user, institution_id)

        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be later than end_date.",
            )

        common_filters = []
        if scoped_inst_id:
            common_filters.append(Application.institution_id == scoped_inst_id)
        if start_date:
            common_filters.append(cast(Application.created_at, Date) >= start_date)
        if end_date:
            common_filters.append(cast(Application.created_at, Date) <= end_date)

        # Active in workflow = not Draft, Approved, Rejected, or Closed
        active_statuses = [
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.UNDER_SCRUTINY,
            ApplicationStatus.RETURNED_FOR_CLARIFICATION,
            ApplicationStatus.EVC_PENDING,
            ApplicationStatus.EVC_SCHEDULED,
            ApplicationStatus.UNDER_REVIEW,
        ]
        active_filters = [*common_filters, Application.status.in_(active_statuses)]
        if workflow_stage:
            active_filters.append(Application.current_stage == workflow_stage.strip())

        # 1. Total Active in Workflow
        total_active = db.scalar(select(func.count(Application.id)).where(*active_filters)) or 0

        # 2. Stage Distribution
        stage_query = (
            select(
                Application.current_stage,
                Application.current_stage_id,
                func.count(Application.id),
            )
            .where(*active_filters)
            .group_by(Application.current_stage, Application.current_stage_id)
        )
        stage_counts = [
            StageCountItem(
                stage_name=stage_name or "Unassigned Stage",
                stage_id=stage_id,
                count=cnt,
            )
            for stage_name, stage_id, cnt in db.execute(stage_query).all()
        ]

        # 3. Ageing Buckets for pending submitted applications
        now_ts = func.now()
        days_pending = func.extract("epoch", now_ts - Application.submitted_at) / 86400
        ageing_query = (
            select(
                func.count(case((days_pending < 30, 1))).label("under_30"),
                func.count(case((and_(days_pending >= 30, days_pending < 60), 1))).label("days_30_to_60"),
                func.count(case((and_(days_pending >= 60, days_pending < 90), 1))).label("days_60_to_90"),
                func.count(case((days_pending >= 90, 1))).label("over_90"),
            )
            .where(
                *common_filters,
                Application.submitted_at.isnot(None),
                Application.status.in_(active_statuses),
            )
        )
        ageing_res = db.execute(ageing_query).one()
        ageing_buckets = AgeingBuckets(
            under_30_days=ageing_res.under_30 or 0,
            days_30_to_60=ageing_res.days_30_to_60 or 0,
            days_60_to_90=ageing_res.days_60_to_90 or 0,
            over_90_days=ageing_res.over_90 or 0,
        )

        # 4. Average Processing Duration for completed applications (submitted -> updated/closed)
        completed_statuses = [
            ApplicationStatus.APPROVED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.CLOSED,
        ]
        duration_query = (
            select(
                func.avg(func.extract("epoch", Application.updated_at - Application.submitted_at) / 86400),
                func.count(Application.id),
            )
            .where(
                *common_filters,
                Application.submitted_at.isnot(None),
                Application.status.in_(completed_statuses),
            )
        )
        avg_days, completed_count = db.execute(duration_query).one()
        avg_processing_days = round(float(avg_days), 1) if avg_days is not None else None

        # 5. Recent Transitions
        recent_transitions_query = (
            select(ApplicationStageHistory)
            .join(Application, ApplicationStageHistory.application_id == Application.id)
            .options(
                joinedload(ApplicationStageHistory.application),
                joinedload(ApplicationStageHistory.acted_by_user),
            )
            .order_by(desc(ApplicationStageHistory.entered_at))
            .limit(10)
        )
        if scoped_inst_id:
            recent_transitions_query = recent_transitions_query.where(
                Application.institution_id == scoped_inst_id
            )

        transitions = [
            RecentActivityItem(
                id=str(sh.id),
                activity_type="stage_transition",
                application_id=sh.application_id,
                application_number=sh.application.application_number if sh.application else None,
                title=f"{sh.action_name or sh.status}",
                description=sh.remarks,
                status=sh.status,
                timestamp=sh.entered_at,
                acted_by=sh.acted_by_user.full_name if sh.acted_by_user else None,
            )
            for sh in db.scalars(recent_transitions_query).all()
        ]

        return WorkflowAnalyticsResponse(
            total_active_in_workflow=total_active,
            stage_distribution=stage_counts,
            ageing_buckets=ageing_buckets,
            average_processing_duration_days=avg_processing_days,
            completed_count=completed_count or 0,
            recent_transitions=transitions,
        )

    @staticmethod
    def get_compliance_analytics(
        db: Session,
        user: User,
        institution_id: Optional[uuid.UUID] = None,
        compliance_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> ComplianceAnalyticsResponse:
        """
        Calculates compliance fulfillment rates, type distributions, overdue counts,
        and document validity/expiry breakdown.
        """
        scoped_inst_id = DashboardService.check_institution_access(user, institution_id)

        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be later than end_date.",
            )

        filters = []
        if scoped_inst_id:
            filters.append(ComplianceRecord.institution_id == scoped_inst_id)
        if compliance_type:
            filters.append(ComplianceRecord.compliance_type.ilike(f"%{compliance_type.strip()}%"))
        if start_date:
            filters.append(cast(ComplianceRecord.created_at, Date) >= start_date)
        if end_date:
            filters.append(cast(ComplianceRecord.created_at, Date) <= end_date)

        # 1. Status Breakdown
        status_query = (
            select(ComplianceRecord.status, func.count(ComplianceRecord.id))
            .where(*filters)
            .group_by(ComplianceRecord.status)
        )
        status_breakdown = {
            (k.value if hasattr(k, "value") else str(k)): v
            for k, v in db.execute(status_query).all()
        }
        total_records = sum(status_breakdown.values())

        # 2. Type Breakdown
        type_query = (
            select(ComplianceRecord.compliance_type, func.count(ComplianceRecord.id))
            .where(*filters)
            .group_by(ComplianceRecord.compliance_type)
        )
        type_breakdown = dict(db.execute(type_query).all())

        # 3. Fulfilment rate: verified / total * 100
        verified_count = status_breakdown.get(ComplianceStatus.VERIFIED.value, 0)
        fulfilment_rate = round((verified_count / total_records * 100), 2) if total_records > 0 else 0.0

        # 4. Overdue count
        today = date.today()
        overdue_query = (
            select(func.count(ComplianceRecord.id))
            .where(
                *filters,
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
                ),
            )
        )
        overdue_count = db.scalar(overdue_query) or 0

        # 5. Upcoming deadlines within 14 days
        upcoming_query = (
            select(func.count(ComplianceRecord.id))
            .where(
                *filters,
                ComplianceRecord.due_date >= today,
                ComplianceRecord.due_date <= today + timedelta(days=14),
                ComplianceRecord.status.in_([
                    ComplianceStatus.PENDING,
                    ComplianceStatus.SUBMITTED,
                    ComplianceStatus.UNDER_VERIFICATION,
                ]),
            )
        )
        upcoming_deadlines_count = db.scalar(upcoming_query) or 0

        # 6. Document Expiry Breakdown
        doc_filters = []
        if scoped_inst_id:
            doc_filters.append(Document.institution_id == scoped_inst_id)

        now = datetime.now()
        doc_expiry_query = (
            select(
                func.count(case((Document.expires_at < now, 1))).label("expired"),
                func.count(
                    case((
                        and_(
                            Document.expires_at >= now,
                            Document.expires_at <= now + timedelta(days=7),
                        ),
                        1,
                    ))
                ).label("expiring_7"),
                func.count(
                    case((
                        and_(
                            Document.expires_at > now + timedelta(days=7),
                            Document.expires_at <= now + timedelta(days=30),
                        ),
                        1,
                    ))
                ).label("expiring_30"),
                func.count(
                    case((
                        and_(
                            Document.expires_at > now + timedelta(days=30),
                            Document.expires_at <= now + timedelta(days=90),
                        ),
                        1,
                    ))
                ).label("expiring_90"),
                func.count(
                    case((
                        or_(
                            Document.expires_at > now + timedelta(days=90),
                            Document.expires_at.is_(None),
                        ),
                        1,
                    ))
                ).label("valid"),
            )
            .where(*doc_filters)
        )
        doc_expiry_row = db.execute(doc_expiry_query).one()
        doc_breakdown = DocumentExpiryBreakdown(
            expired=doc_expiry_row.expired or 0,
            expiring_7_days=doc_expiry_row.expiring_7 or 0,
            expiring_30_days=doc_expiry_row.expiring_30 or 0,
            expiring_90_days=doc_expiry_row.expiring_90 or 0,
            valid=doc_expiry_row.valid or 0,
        )

        return ComplianceAnalyticsResponse(
            total_records=total_records,
            status_breakdown=status_breakdown,
            type_breakdown=type_breakdown,
            fulfilment_rate=fulfilment_rate,
            overdue_count=overdue_count,
            upcoming_deadlines_count=upcoming_deadlines_count,
            document_expiry_breakdown=doc_breakdown,
        )

    @staticmethod
    def get_alerts_analytics(
        db: Session,
        user: User,
    ) -> AlertsAnalyticsResponse:
        """
        Calculates user-specific and system-wide alert metrics, priority breakdown,
        and statutory escalations.
        """
        filters = []
        if user.role in [UserRole.INSTITUTION_USER, UserRole.REVIEWER]:
            filters.append(Notification.recipient_user_id == user.id)

        # 1. Total & Status counts
        status_query = (
            select(Notification.status, func.count(Notification.id))
            .where(*filters)
            .group_by(Notification.status)
        )
        status_map = {
            (k.value if hasattr(k, "value") else str(k)): v
            for k, v in db.execute(status_query).all()
        }
        total_notifs = sum(status_map.values())
        unread_cnt = status_map.get(NotificationStatus.UNREAD.value, 0)
        read_cnt = status_map.get(NotificationStatus.READ.value, 0)
        archived_cnt = status_map.get(NotificationStatus.ARCHIVED.value, 0)

        # 2. Priority breakdown
        priority_query = (
            select(Notification.priority, func.count(Notification.id))
            .where(*filters)
            .group_by(Notification.priority)
        )
        priority_breakdown = {
            (k.value if hasattr(k, "value") else str(k)): v
            for k, v in db.execute(priority_query).all()
        }

        # 3. Type breakdown
        type_query = (
            select(Notification.notification_type, func.count(Notification.id))
            .where(*filters)
            .group_by(Notification.notification_type)
        )
        type_breakdown = {
            (k.value if hasattr(k, "value") else str(k)): v
            for k, v in db.execute(type_query).all()
        }

        # 4. Recent alerts (latest 10)
        recent_notifs = (
            db.scalars(
                select(Notification)
                .where(*filters)
                .order_by(desc(Notification.created_at))
                .limit(10)
            )
            .all()
        )
        recent_alerts = [NotificationResponse.model_validate(n) for n in recent_notifs]

        # 5. Escalation History
        escalations_count = 0
        recent_escalations = []
        if user.role in [UserRole.ADMIN, UserRole.AICTE_OFFICIAL]:
            escalations_count = db.scalar(select(func.count(EscalationHistory.id))) or 0
            esc_rows = (
                db.scalars(
                    select(EscalationHistory)
                    .order_by(desc(EscalationHistory.created_at))
                    .limit(10)
                )
                .all()
            )
            recent_escalations = [EscalationHistoryResponse.model_validate(e) for e in esc_rows]

        return AlertsAnalyticsResponse(
            total_notifications=total_notifs,
            unread_count=unread_cnt,
            read_count=read_cnt,
            archived_count=archived_cnt,
            priority_breakdown=priority_breakdown,
            type_breakdown=type_breakdown,
            recent_alerts=recent_alerts,
            escalations_count=escalations_count,
            recent_escalations=recent_escalations,
        )
