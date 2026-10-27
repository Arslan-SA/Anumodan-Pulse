"""
AICTE FlowOps — User Model

Represents a person who uses the platform (Admin, Official, Reviewer, Institution User).
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.institution import Institution
    from app.models.stage_history import ApplicationStageHistory
    from app.models.compliance import ComplianceRecord
    from app.models.document import Document


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        String(50),
        default=UserRole.INSTITUTION_USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Optional association with an institution (for INSTITUTION_USER roles)
    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("institutions.id", ondelete="SET NULL"),
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
    institution: Mapped[Optional["Institution"]] = relationship(
        "Institution",
        back_populates="users",
    )
    stage_actions: Mapped[List["ApplicationStageHistory"]] = relationship(
        "ApplicationStageHistory",
        back_populates="acted_by_user",
    )
    verified_compliance_records: Mapped[List["ComplianceRecord"]] = relationship(
        "ComplianceRecord",
        back_populates="verified_by_user",
    )
    uploaded_documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="uploaded_by_user",
    )

    def __repr__(self) -> str:
        return f"<User(email='{self.email}', role='{self.role}')>"
