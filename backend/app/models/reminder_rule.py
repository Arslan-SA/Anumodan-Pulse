"""
AICTE FlowOps — ReminderRule Model

Defines configurable notification and deadline reminder rules.
Allows administrators to adjust reminder schedules and priorities without code changes.
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import NotificationPriority


class ReminderRule(Base):
    __tablename__ = "reminder_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    days_before_deadline: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    overdue_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    priority: Mapped[NotificationPriority] = mapped_column(
        String(20),
        default=NotificationPriority.MEDIUM,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ReminderRule(name='{self.name}', event='{self.event_type}', active={self.is_active})>"
