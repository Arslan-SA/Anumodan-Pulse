"""
AICTE FlowOps — Deadline Monitoring & Escalation Service

Monitors:
- Compliance records due soon or overdue
- Documents approaching expiry or expired
- Applications pending beyond configured processing thresholds
- Triggering configurable escalations and immutable escalation audit histories
"""

from datetime import date, datetime, timedelta, timezone
import math
from typing import Dict, List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.application import Application
from app.models.compliance import ComplianceRecord
from app.models.document import Document
from app.models.enums import (
    ApplicationStatus,
    ComplianceStatus,
    NotificationPriority,
    NotificationType,
    UserRole,
)
from app.models.escalation_history import EscalationHistory
from app.models.reminder_rule import ReminderRule
from app.models.user import User
from app.schemas.reminder_rule import ReminderRuleCreate, ReminderRuleUpdate
from app.services.notification_service import NotificationService


class DeadlineService:

    # ── Reminder Rules Administration (Admin-Only) ────────────────────

    @staticmethod
    def create_reminder_rule(
        db: Session,
        admin_user: User,
        payload: ReminderRuleCreate,
    ) -> ReminderRule:
        """Create a new configurable reminder schedule (Admin only)."""
        if admin_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can configure reminder rules.",
            )

        # Validate duplicate active rule for same event and interval
        if payload.is_active:
            duplicate = db.scalar(
                select(ReminderRule.id).where(
                    ReminderRule.event_type == payload.event_type,
                    ReminderRule.days_before_deadline == payload.days_before_deadline,
                    ReminderRule.overdue_days == payload.overdue_days,
                    ReminderRule.is_active.is_(True),
                )
            )
            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An active reminder rule already exists for this event type and interval.",
                )

        rule = ReminderRule(
            name=payload.name.strip(),
            event_type=payload.event_type.strip(),
            days_before_deadline=payload.days_before_deadline,
            overdue_days=payload.overdue_days,
            target_role=payload.target_role.strip() if payload.target_role else None,
            priority=payload.priority,
            is_active=payload.is_active,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def list_reminder_rules(
        db: Session,
        active_only: bool = False,
    ) -> List[ReminderRule]:
        """List configured reminder rules."""
        query = select(ReminderRule).order_by(ReminderRule.created_at.desc())
        if active_only:
            query = query.where(ReminderRule.is_active.is_(True))
        return list(db.scalars(query).all())

    @staticmethod
    def get_reminder_rule(db: Session, rule_id: uuid.UUID) -> ReminderRule:
        rule = db.scalar(select(ReminderRule).where(ReminderRule.id == rule_id))
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reminder rule '{rule_id}' not found.",
            )
        return rule

    @staticmethod
    def update_reminder_rule(
        db: Session,
        admin_user: User,
        rule_id: uuid.UUID,
        payload: ReminderRuleUpdate,
    ) -> ReminderRule:
        """Update a reminder rule."""
        if admin_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can update reminder rules.",
            )

        rule = DeadlineService.get_reminder_rule(db, rule_id)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)

        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def toggle_reminder_rule_status(
        db: Session,
        admin_user: User,
        rule_id: uuid.UUID,
        is_active: bool,
    ) -> ReminderRule:
        """Toggle active evaluation of a reminder rule."""
        if admin_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can update reminder rule status.",
            )

        rule = DeadlineService.get_reminder_rule(db, rule_id)
        rule.is_active = is_active
        db.commit()
        db.refresh(rule)
        return rule

    # ── Escalations ───────────────────────────────────────────────────

    @staticmethod
    def list_escalations(
        db: Session,
        user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[EscalationHistory], int, int, int, int]:
        """List escalation history records with role-based access control."""
        query = select(EscalationHistory).order_by(EscalationHistory.created_at.desc())

        if user.role == UserRole.INSTITUTION_USER:
            # Institution users see only escalations affecting their institution
            if not user.institution_id:
                return [], 0, page, page_size, 0
            # Match application or compliance belonging to user.institution_id
            query = query.where(
                or_(
                    EscalationHistory.entity_id.in_(
                        select(Application.id).where(Application.institution_id == user.institution_id)
                    ),
                    EscalationHistory.entity_id.in_(
                        select(ComplianceRecord.id).where(ComplianceRecord.institution_id == user.institution_id)
                    ),
                )
            )

        count_stmt = select(func.count(EscalationHistory.id))
        total = db.scalar(count_stmt) or 0
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size

        items = list(db.scalars(query.offset(offset).limit(page_size)).all())
        return items, total, page, page_size, total_pages

    # ── Periodic Deadline Monitoring Engine ───────────────────────────

    @staticmethod
    def evaluate_deadlines_and_reminders(db: Session) -> Dict[str, int]:
        """
        Evaluate statutory deadlines, expiry projections, and configured escalation rules.
        Idempotent and safe to run on repeat schedules.
        """
        stats = {
            "compliance_due_soon": 0,
            "compliance_overdue": 0,
            "compliance_escalations": 0,
            "documents_expiring": 0,
            "documents_expired": 0,
            "applications_escalated": 0,
        }

        today = date.today()
        now_utc = datetime.now(timezone.utc)

        # 1. Fetch active Reminder Rules
        active_rules = list(
            db.scalars(select(ReminderRule).where(ReminderRule.is_active.is_(True))).all()
        )

        # Windows for compliance due soon
        due_soon_rules = [r for r in active_rules if r.event_type == "COMPLIANCE_DUE_SOON" and r.days_before_deadline]
        due_soon_windows = [r.days_before_deadline for r in due_soon_rules] or settings.reminder_windows_list

        # Windows for compliance overdue escalations
        overdue_rules = [r for r in active_rules if r.event_type == "COMPLIANCE_OVERDUE" and r.overdue_days]
        overdue_escalation_threshold = overdue_rules[0].overdue_days if overdue_rules else settings.default_escalation_overdue_days

        # Windows for document expiry
        doc_exp_rules = [r for r in active_rules if r.event_type == "DOCUMENT_EXPIRING" and r.days_before_deadline]
        doc_exp_windows = [r.days_before_deadline for r in doc_exp_rules] or [30, 15, 7]

        # Windows for application pending escalations
        app_pending_rules = [r for r in active_rules if r.event_type == "APPLICATION_PENDING" and r.overdue_days]
        app_pending_threshold_days = app_pending_rules[0].overdue_days if app_pending_rules else 14

        # ── Check Compliance Due Soon ─────────────────────────────────
        pending_compliances = list(
            db.scalars(
                select(ComplianceRecord).where(
                    ComplianceRecord.status.in_([ComplianceStatus.PENDING, ComplianceStatus.REJECTED]),
                    ComplianceRecord.due_date.is_not(None),
                )
            ).all()
        )

        for rec in pending_compliances:
            if not rec.due_date:
                continue

            days_until_due = (rec.due_date - today).days

            # Due soon warnings
            if days_until_due > 0 and days_until_due in due_soon_windows:
                inst_users = db.scalars(
                    select(User).where(User.institution_id == rec.institution_id, User.is_active.is_(True))
                ).all()
                for u in inst_users:
                    dedup_key = f"COMPL_DUE_SOON:{rec.id}:{rec.due_date}:{days_until_due}:{u.id}"
                    created = NotificationService.send_notification(
                        db=db,
                        recipient_user_id=u.id,
                        notification_type=NotificationType.COMPLIANCE_DUE_SOON,
                        title=f"Statutory Deadline in {days_until_due} Days: {rec.title}",
                        message=(
                            f"Statutory undertaking '{rec.title}' ({rec.compliance_type}) "
                            f"is due on {rec.due_date.isoformat()} ({days_until_due} days remaining)."
                        ),
                        related_compliance_id=rec.id,
                        related_application_id=rec.application_id,
                        priority=NotificationPriority.HIGH if days_until_due <= 3 else NotificationPriority.MEDIUM,
                        dedup_key=dedup_key,
                    )
                    if created:
                        stats["compliance_due_soon"] += 1

            # Overdue alerts & escalation
            elif days_until_due < 0:
                overdue_by = abs(days_until_due)
                inst_users = db.scalars(
                    select(User).where(User.institution_id == rec.institution_id, User.is_active.is_(True))
                ).all()
                for u in inst_users:
                    dedup_key = f"COMPL_OVERDUE:{rec.id}:{rec.due_date}:{u.id}"
                    created = NotificationService.send_notification(
                        db=db,
                        recipient_user_id=u.id,
                        notification_type=NotificationType.COMPLIANCE_OVERDUE,
                        title=f"Statutory Compliance Overdue: {rec.title}",
                        message=(
                            f"Statutory undertaking '{rec.title}' was due on {rec.due_date.isoformat()} "
                            f"and is currently {overdue_by} days overdue."
                        ),
                        related_compliance_id=rec.id,
                        related_application_id=rec.application_id,
                        priority=NotificationPriority.CRITICAL,
                        dedup_key=dedup_key,
                    )
                    if created:
                        stats["compliance_overdue"] += 1

                # Escalation beyond threshold
                if overdue_by >= overdue_escalation_threshold:
                    esc_dedup = f"ESC_COMPLIANCE:{rec.id}:{rec.due_date}:{overdue_escalation_threshold}"
                    already_escalated = db.scalar(
                        select(EscalationHistory.id).where(EscalationHistory.dedup_key == esc_dedup)
                    )
                    if not already_escalated:
                        esc = EscalationHistory(
                            entity_type="ComplianceRecord",
                            entity_id=rec.id,
                            rule_name=f"Compliance Overdue > {overdue_escalation_threshold} Days",
                            escalation_level=1,
                            escalated_to_role=UserRole.AICTE_OFFICIAL.value,
                            reason=f"Compliance record '{rec.title}' is overdue by {overdue_by} days (due {rec.due_date}).",
                            dedup_key=esc_dedup,
                        )
                        db.add(esc)
                        db.commit()
                        stats["compliance_escalations"] += 1

                        # Alert officials
                        officials = db.scalars(
                            select(User).where(
                                User.role.in_([UserRole.AICTE_OFFICIAL, UserRole.ADMIN]),
                                User.is_active.is_(True),
                            )
                        ).all()
                        for off in officials:
                            NotificationService.send_notification(
                                db=db,
                                recipient_user_id=off.id,
                                notification_type=NotificationType.ESCALATION,
                                title=f"Compliance Escalation: {rec.title}",
                                message=(
                                    f"Institution compliance '{rec.title}' is {overdue_by} days overdue. "
                                    f"Escalated for supervisory administrative attention."
                                ),
                                related_compliance_id=rec.id,
                                priority=NotificationPriority.CRITICAL,
                                dedup_key=f"ESC_NOTIF_COMPL:{rec.id}:{off.id}",
                            )

        # ── Check Documents Expiring ──────────────────────────────────
        expiring_docs = list(
            db.scalars(
                select(Document).where(Document.expires_at.is_not(None))
            ).all()
        )

        for d in expiring_docs:
            if not d.expires_at:
                continue

            # Standardize timezone
            doc_expires_at = d.expires_at if d.expires_at.tzinfo else d.expires_at.replace(tzinfo=timezone.utc)
            days_left = (doc_expires_at.date() - today).days

            if days_left > 0 and days_left in doc_exp_windows:
                inst_users = db.scalars(
                    select(User).where(User.institution_id == d.institution_id, User.is_active.is_(True))
                ).all()
                for u in inst_users:
                    dedup_key = f"DOC_EXPIRING:{d.id}:{days_left}:{u.id}"
                    created = NotificationService.send_notification(
                        db=db,
                        recipient_user_id=u.id,
                        notification_type=NotificationType.DOCUMENT_EXPIRING,
                        title=f"Document Expiring in {days_left} Days: {d.document_name}",
                        message=f"Mandatory document '{d.document_name}' ({d.document_type}) expires on {doc_expires_at.date().isoformat()}.",
                        related_document_id=d.id,
                        related_application_id=d.application_id,
                        related_compliance_id=d.compliance_record_id,
                        priority=NotificationPriority.HIGH if days_left <= 7 else NotificationPriority.MEDIUM,
                        dedup_key=dedup_key,
                    )
                    if created:
                        stats["documents_expiring"] += 1

            elif days_left <= 0:
                inst_users = db.scalars(
                    select(User).where(User.institution_id == d.institution_id, User.is_active.is_(True))
                ).all()
                for u in inst_users:
                    dedup_key = f"DOC_EXPIRED:{d.id}:{doc_expires_at.date()}:{u.id}"
                    created = NotificationService.send_notification(
                        db=db,
                        recipient_user_id=u.id,
                        notification_type=NotificationType.DOCUMENT_EXPIRED,
                        title=f"Document Expired: {d.document_name}",
                        message=f"Document '{d.document_name}' expired on {doc_expires_at.date().isoformat()}. Please upload renewed documentation.",
                        related_document_id=d.id,
                        related_application_id=d.application_id,
                        related_compliance_id=d.compliance_record_id,
                        priority=NotificationPriority.CRITICAL,
                        dedup_key=dedup_key,
                    )
                    if created:
                        stats["documents_expired"] += 1

        # ── Check Applications Pending Beyond Threshold ────────────────
        active_apps = list(
            db.scalars(
                select(Application).where(
                    Application.status.not_in([
                        ApplicationStatus.DRAFT,
                        ApplicationStatus.APPROVED,
                        ApplicationStatus.REJECTED,
                        ApplicationStatus.CLOSED,
                    ])
                )
            ).all()
        )

        for app in active_apps:
            ref_time = app.submitted_at or app.created_at
            if not ref_time:
                continue

            ref_dt = ref_time if ref_time.tzinfo else ref_time.replace(tzinfo=timezone.utc)
            pending_days = (now_utc - ref_dt).days

            if pending_days >= app_pending_threshold_days:
                app_esc_dedup = f"ESC_APP:{app.id}:{app_pending_threshold_days}"
                already_esc = db.scalar(
                    select(EscalationHistory.id).where(EscalationHistory.dedup_key == app_esc_dedup)
                )
                if not already_esc:
                    esc = EscalationHistory(
                        entity_type="Application",
                        entity_id=app.id,
                        rule_name=f"Application Inactivity > {app_pending_threshold_days} Days",
                        escalation_level=1,
                        escalated_to_role=UserRole.AICTE_OFFICIAL.value,
                        reason=(
                            f"Application {app.application_number} in stage '{app.current_stage or app.status}' "
                            f"has been pending without final statutory decision for {pending_days} days."
                        ),
                        dedup_key=app_esc_dedup,
                    )
                    db.add(esc)
                    db.commit()
                    stats["applications_escalated"] += 1

                    # Alert supervisory officials
                    officials = db.scalars(
                        select(User).where(
                            User.role.in_([UserRole.AICTE_OFFICIAL, UserRole.ADMIN]),
                            User.is_active.is_(True),
                        )
                    ).all()
                    for off in officials:
                        NotificationService.send_notification(
                            db=db,
                            recipient_user_id=off.id,
                            notification_type=NotificationType.ESCALATION,
                            title=f"Application Escalation: {app.application_number}",
                            message=(
                                f"Application {app.application_number} has remained pending for {pending_days} days. "
                                f"Escalated to supervisory officials."
                            ),
                            related_application_id=app.id,
                            priority=NotificationPriority.CRITICAL,
                            dedup_key=f"ESC_NOTIF_APP:{app.id}:{off.id}",
                        )

        return stats
