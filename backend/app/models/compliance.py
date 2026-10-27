"""
AICTE FlowOps — ComplianceRecord Model

Represents a compliance requirement, statutory undertaking, or condition
associated with an institution or application.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ComplianceStatus

if TYPE_CHECKING:
    from app.models.institution import Institution
    from app.models.application import Application
    from app.models.user import User
    from app.models.document import Document
    from app.models.compliance_history import ComplianceHistory


class ComplianceRecord(Base):
    __tablename__ = "compliance_records"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    compliance_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[ComplianceStatus] = mapped_column(
        String(50),
        default=ComplianceStatus.PENDING,
        nullable=False,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ───────────────────────────────────────────────────
    institution: Mapped["Institution"] = relationship(
        "Institution",
        back_populates="compliance_records",
    )
    application: Mapped[Optional["Application"]] = relationship(
        "Application",
        back_populates="compliance_records",
    )
    verified_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="verified_compliance_records",
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="compliance_record",
    )
    histories: Mapped[List["ComplianceHistory"]] = relationship(
        "ComplianceHistory",
        back_populates="compliance_record",
        cascade="all, delete-orphan",
        order_by="ComplianceHistory.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<ComplianceRecord(title='{self.title}', status='{self.status}')>"
