"""
AICTE FlowOps — Application Model

Represents an approval application submitted by an institution.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ApplicationStatus

if TYPE_CHECKING:
    from app.models.compliance import ComplianceRecord
    from app.models.document import Document
    from app.models.institution import Institution
    from app.models.stage_history import ApplicationStageHistory
    from app.models.workflow_definition import WorkflowDefinition
    from app.models.workflow_stage import WorkflowStage


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    application_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    application_type: Mapped[str] = mapped_column(String(100), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        String(50),
        default=ApplicationStatus.DRAFT,
        nullable=False,
    )
    workflow_definition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    current_stage_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_stages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    current_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
        back_populates="applications",
    )
    workflow_definition: Mapped[Optional["WorkflowDefinition"]] = relationship(
        "WorkflowDefinition",
        back_populates="applications",
    )
    current_stage_rel: Mapped[Optional["WorkflowStage"]] = relationship(
        "WorkflowStage",
        foreign_keys=[current_stage_id],
        back_populates="current_applications",
    )
    stage_histories: Mapped[List["ApplicationStageHistory"]] = relationship(
        "ApplicationStageHistory",
        back_populates="application",
    )
    compliance_records: Mapped[List["ComplianceRecord"]] = relationship(
        "ComplianceRecord",
        back_populates="application",
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="application",
    )

    def __repr__(self) -> str:
        return f"<Application(number='{self.application_number}', status='{self.status}')>"
