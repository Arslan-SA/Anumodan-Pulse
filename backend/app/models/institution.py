"""
AICTE FlowOps — Institution Model

Represents a technical institution registered on the platform.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.application import Application
    from app.models.compliance import ComplianceRecord
    from app.models.document import Document


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    institution_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    institution_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

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
    # Explicit deletion behavior: preserve institution records and related history
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="institution",
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="institution",
    )
    compliance_records: Mapped[List["ComplianceRecord"]] = relationship(
        "ComplianceRecord",
        back_populates="institution",
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="institution",
    )

    def __repr__(self) -> str:
        return f"<Institution(code='{self.institution_code}', name='{self.institution_name}')>"
