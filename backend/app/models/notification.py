"""
AICTE FlowOps — Notification Model

Represents user-facing alerts, workflow notifications, compliance reminders,
and statutory escalation messages.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import NotificationPriority, NotificationStatus, NotificationType

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.compliance import ComplianceRecord
    from app.models.document import Document
    from app.models.user import User


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    related_application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_compliance_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("compliance_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    priority: Mapped[NotificationPriority] = mapped_column(
        String(20),
        default=NotificationPriority.MEDIUM,
        nullable=False,
        index=True,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        String(20),
        default=NotificationStatus.UNREAD,
        nullable=False,
        index=True,
    )
    dedup_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ───────────────────────────────────────────────────
    recipient_user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
    )
    related_application: Mapped[Optional["Application"]] = relationship("Application")
    related_compliance: Mapped[Optional["ComplianceRecord"]] = relationship("ComplianceRecord")
    related_document: Mapped[Optional["Document"]] = relationship("Document")

    __table_args__ = (
        Index("ix_notifications_user_status", "recipient_user_id", "status"),
        Index("ix_notifications_user_created", "recipient_user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Notification(type='{self.notification_type}', recipient='{self.recipient_user_id}', status='{self.status}')>"
