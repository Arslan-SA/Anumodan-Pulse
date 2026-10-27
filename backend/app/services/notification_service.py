"""
AICTE FlowOps — Notification Service

Encapsulates:
- Independent notification generation and recipient resolution
- Idempotency & deduplication keys to prevent duplicate alerts
- Status lifecycle (UNREAD -> READ, ARCHIVED)
- User privacy and access boundary enforcement
- Service-triggered reusable templates for workflow and compliance events
"""

from datetime import datetime, timezone
import math
from typing import List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application
from app.models.compliance import ComplianceRecord
from app.models.document import Document
from app.models.enums import NotificationPriority, NotificationStatus, NotificationType, UserRole
from app.models.escalation_history import EscalationHistory
from app.models.notification import Notification
from app.models.user import User



class NotificationService:

    @staticmethod
    def send_notification(
        db: Session,
        recipient_user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        related_application_id: Optional[uuid.UUID] = None,
        related_compliance_id: Optional[uuid.UUID] = None,
        related_document_id: Optional[uuid.UUID] = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        dedup_key: Optional[str] = None,
    ) -> Optional[Notification]:
        """
        Create and persist a notification for an authenticated user.
        If a dedup_key is provided and a notification with the same dedup_key
        already exists for this recipient, duplicate creation is prevented.
        """
        # Deduplication check
        if dedup_key:
            existing = db.scalar(
                select(Notification.id).where(
                    Notification.recipient_user_id == recipient_user_id,
                    Notification.dedup_key == dedup_key,
                )
            )
            if existing:
                return None

        # Verify recipient exists and is active
        user = db.scalar(select(User).where(User.id == recipient_user_id, User.is_active.is_(True)))
        if not user:
            return None

        notif = Notification(
            recipient_user_id=recipient_user_id,
            notification_type=notification_type,
            title=title.strip(),
            message=message.strip(),
            related_application_id=related_application_id,
            related_compliance_id=related_compliance_id,
            related_document_id=related_document_id,
            priority=priority,
            status=NotificationStatus.UNREAD,
            dedup_key=dedup_key,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def list_user_notifications(
        db: Session,
        user: User,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        notification_type: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Tuple[List[Notification], int, int, int, int]:
        """
        Retrieve notifications strictly scoped to the authenticated user.
        Admins cannot see other users' private alerts through this endpoint.
        """
        query = (
            select(Notification)
            .where(Notification.recipient_user_id == user.id)
            .order_by(Notification.created_at.desc())
        )

        if status_filter:
            query = query.where(Notification.status == status_filter)
        if notification_type:
            query = query.where(Notification.notification_type == notification_type)
        if priority:
            query = query.where(Notification.priority == priority)

        # Count total
        count_stmt = select(func.count(Notification.id)).where(Notification.recipient_user_id == user.id)
        if status_filter:
            count_stmt = count_stmt.where(Notification.status == status_filter)
        if notification_type:
            count_stmt = count_stmt.where(Notification.notification_type == notification_type)
        if priority:
            count_stmt = count_stmt.where(Notification.priority == priority)

        total = db.scalar(count_stmt) or 0
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size

        items = list(db.scalars(query.offset(offset).limit(page_size)).all())
        return items, total, page, page_size, total_pages

    @staticmethod
    def get_user_notification(
        db: Session,
        notification_id: uuid.UUID,
        user: User,
    ) -> Notification:
        """
        Retrieve a single notification, verifying recipient ownership.
        Returns 404 if not found or belongs to another user.
        """
        notif = db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.recipient_user_id == user.id,
            )
        )
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification '{notification_id}' not found.",
            )
        return notif

    @staticmethod
    def mark_as_read(
        db: Session,
        notification_id: uuid.UUID,
        user: User,
    ) -> Notification:
        """Mark a notification as READ with UTC timestamp."""
        notif = NotificationService.get_user_notification(db, notification_id, user)
        if notif.status != NotificationStatus.READ:
            notif.status = NotificationStatus.READ
            notif.read_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(notif)
        return notif

    @staticmethod
    def mark_all_as_read(db: Session, user: User) -> int:
        """Mark all UNREAD notifications belonging to the user as READ."""
        unreads = list(
            db.scalars(
                select(Notification).where(
                    Notification.recipient_user_id == user.id,
                    Notification.status == NotificationStatus.UNREAD,
                )
            ).all()
        )
        now_utc = datetime.now(timezone.utc)
        for n in unreads:
            n.status = NotificationStatus.READ
            n.read_at = now_utc

        db.commit()
        return len(unreads)

    @staticmethod
    def archive_notification(
        db: Session,
        notification_id: uuid.UUID,
        user: User,
    ) -> Notification:
        """Archive a notification."""
        notif = NotificationService.get_user_notification(db, notification_id, user)
        notif.status = NotificationStatus.ARCHIVED
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def get_unread_count(db: Session, user: User) -> int:
        """Count unread notifications for authenticated user."""
        count = db.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_user_id == user.id,
                Notification.status == NotificationStatus.UNREAD,
            )
        )
        return count or 0

    # ── Service Event Trigger Templates ────────────────────────────────

    @staticmethod
    def notify_application_submitted(db: Session, application: Application, actor_user: User) -> None:
        """Notify relevant AICTE officials when an application is submitted."""
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
                notification_type=NotificationType.APPLICATION_SUBMITTED,
                title=f"New Application Submitted: {application.application_number}",
                message=(
                    f"Application {application.application_number} ({application.application_type}) "
                    f"has been submitted for statutory scrutiny."
                ),
                related_application_id=application.id,
                priority=NotificationPriority.MEDIUM,
                dedup_key=f"APP_SUBMITTED:{application.id}:{off.id}",
            )

    @staticmethod
    def notify_application_returned(
        db: Session,
        application: Application,
        reason: str,
        actor_user: User,
    ) -> None:
        """Notify institution users when an application is returned for clarification."""
        inst_users = db.scalars(
            select(User).where(
                User.institution_id == application.institution_id,
                User.is_active.is_(True),
            )
        ).all()

        for u in inst_users:
            NotificationService.send_notification(
                db=db,
                recipient_user_id=u.id,
                notification_type=NotificationType.APPLICATION_RETURNED,
                title=f"Clarification Required: {application.application_number}",
                message=(
                    f"Application {application.application_number} requires clarification. "
                    f"Remarks: {reason}"
                ),
                related_application_id=application.id,
                priority=NotificationPriority.HIGH,
                dedup_key=f"APP_RETURNED:{application.id}:{datetime.now(timezone.utc).date()}:{u.id}",
            )

    @staticmethod
    def notify_application_stage_updated(
        db: Session,
        application: Application,
        previous_stage: Optional[str],
        new_stage: str,
        actor_user: User,
    ) -> None:
        """Notify institution when workflow stage progresses."""
        inst_users = db.scalars(
            select(User).where(
                User.institution_id == application.institution_id,
                User.is_active.is_(True),
            )
        ).all()

        for u in inst_users:
            NotificationService.send_notification(
                db=db,
                recipient_user_id=u.id,
                notification_type=NotificationType.APPLICATION_STAGE_UPDATED,
                title=f"Stage Advanced: {application.application_number}",
                message=f"Application {application.application_number} transitioned from '{previous_stage or 'Initial'}' to '{new_stage}'.",
                related_application_id=application.id,
                priority=NotificationPriority.LOW,
                dedup_key=f"STAGE_UPDATE:{application.id}:{new_stage}:{u.id}",
            )

    @staticmethod
    def notify_compliance_submitted(db: Session, compliance_record: ComplianceRecord) -> None:
        """Notify AICTE officials that a compliance record was submitted for verification."""
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
                notification_type=NotificationType.COMPLIANCE_SUBMITTED,
                title=f"Compliance Submitted: {compliance_record.title}",
                message=(
                    f"Institution has submitted statutory compliance '{compliance_record.title}' "
                    f"({compliance_record.compliance_type}) for official verification."
                ),
                related_compliance_id=compliance_record.id,
                related_application_id=compliance_record.application_id,
                priority=NotificationPriority.MEDIUM,
                dedup_key=f"COMPL_SUBMITTED:{compliance_record.id}:{off.id}",
            )

    @staticmethod
    def notify_compliance_verified(
        db: Session,
        compliance_record: ComplianceRecord,
        official_user: User,
        remarks: Optional[str] = None,
    ) -> None:
        """Notify institution users when compliance submission is verified."""
        inst_users = db.scalars(
            select(User).where(
                User.institution_id == compliance_record.institution_id,
                User.is_active.is_(True),
            )
        ).all()

        for u in inst_users:
            msg = f"Your statutory compliance '{compliance_record.title}' has been verified by the competent authority."
            if remarks:
                msg += f" Remarks: {remarks}"
            NotificationService.send_notification(
                db=db,
                recipient_user_id=u.id,
                notification_type=NotificationType.COMPLIANCE_VERIFIED,
                title=f"Compliance Verified: {compliance_record.title}",
                message=msg,
                related_compliance_id=compliance_record.id,
                related_application_id=compliance_record.application_id,
                priority=NotificationPriority.MEDIUM,
                dedup_key=f"COMPL_VERIFIED:{compliance_record.id}:{u.id}",
            )

    @staticmethod
    def notify_compliance_rejected(
        db: Session,
        compliance_record: ComplianceRecord,
        official_user: User,
        reason: str,
    ) -> None:
        """Notify institution users when compliance submission is rejected."""
        inst_users = db.scalars(
            select(User).where(
                User.institution_id == compliance_record.institution_id,
                User.is_active.is_(True),
            )
        ).all()

        for u in inst_users:
            NotificationService.send_notification(
                db=db,
                recipient_user_id=u.id,
                notification_type=NotificationType.COMPLIANCE_REJECTED,
                title=f"Compliance Deficiencies: {compliance_record.title}",
                message=f"Compliance '{compliance_record.title}' was rejected. Deficiency reason: {reason}",
                related_compliance_id=compliance_record.id,
                related_application_id=compliance_record.application_id,
                priority=NotificationPriority.HIGH,
                dedup_key=f"COMPL_REJECTED:{compliance_record.id}:{datetime.now(timezone.utc).date()}:{u.id}",
            )
