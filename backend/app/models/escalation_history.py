"""
AICTE FlowOps — EscalationHistory Model

Maintains an immutable historical record of statutory deadline escalations,
alerting supervisory officials while strictly remaining informational (never altering approval status).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class EscalationHistory(Base):
    __tablename__ = "escalation_histories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    escalation_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    escalated_to_role: Mapped[str] = mapped_column(String(50), nullable=False)
    escalated_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    dedup_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ── Relationships ───────────────────────────────────────────────────
    escalated_to_user: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<EscalationHistory(entity='{self.entity_type}:{self.entity_id}', level={self.escalation_level})>"
