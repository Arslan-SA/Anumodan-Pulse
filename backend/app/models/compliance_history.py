"""
AICTE FlowOps — ComplianceHistory Model

Chronicles the verification, submission, and audit lifecycle of compliance records
and statutory undertakings.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.compliance import ComplianceRecord
    from app.models.user import User


class ComplianceHistory(Base):
    __tablename__ = "compliance_histories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    compliance_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("compliance_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acted_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ───────────────────────────────────────────────────
    compliance_record: Mapped["ComplianceRecord"] = relationship(
        "ComplianceRecord",
        back_populates="histories",
    )
    acted_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="compliance_actions",
    )

    def __repr__(self) -> str:
        return f"<ComplianceHistory(action='{self.action}', to_status='{self.to_status}')>"
