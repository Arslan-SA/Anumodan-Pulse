"""
AICTE FlowOps — Document Model

Represents document metadata associated with an institution, application, or compliance record.
Stores metadata and object-storage keys; does not store raw file bytes.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.institution import Institution
    from app.models.application import Application
    from app.models.compliance import ComplianceRecord
    from app.models.user import User


class Document(Base):
    __tablename__ = "documents"

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
    compliance_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("compliance_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    uploaded_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ───────────────────────────────────────────────────
    institution: Mapped["Institution"] = relationship(
        "Institution",
        back_populates="documents",
    )
    application: Mapped[Optional["Application"]] = relationship(
        "Application",
        back_populates="documents",
    )
    compliance_record: Mapped[Optional["ComplianceRecord"]] = relationship(
        "ComplianceRecord",
        back_populates="documents",
    )
    uploaded_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="uploaded_documents",
    )

    def __repr__(self) -> str:
        return f"<Document(name='{self.document_name}', type='{self.document_type}')>"
