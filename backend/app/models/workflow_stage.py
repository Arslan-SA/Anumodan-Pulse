"""
AICTE FlowOps — WorkflowStage Model

Represents a configurable stage in an approval workflow (e.g. Scrutiny, EVC, Committee Review).
Decoupled and extensible without hardcoded transitions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.stage_history import ApplicationStageHistory
    from app.models.workflow_definition import WorkflowDefinition
    from app.models.workflow_transition import WorkflowTransition


class WorkflowStage(Base):
    __tablename__ = "workflow_stages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_definition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sequence_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ───────────────────────────────────────────────────
    workflow_definition: Mapped[Optional["WorkflowDefinition"]] = relationship(
        "WorkflowDefinition",
        back_populates="stages",
    )
    stage_histories: Mapped[List["ApplicationStageHistory"]] = relationship(
        "ApplicationStageHistory",
        back_populates="workflow_stage",
    )
    outgoing_transitions: Mapped[List["WorkflowTransition"]] = relationship(
        "WorkflowTransition",
        foreign_keys="WorkflowTransition.from_stage_id",
        back_populates="from_stage",
        cascade="all, delete-orphan",
    )
    incoming_transitions: Mapped[List["WorkflowTransition"]] = relationship(
        "WorkflowTransition",
        foreign_keys="WorkflowTransition.to_stage_id",
        back_populates="to_stage",
        cascade="all, delete-orphan",
    )
    current_applications: Mapped[List["Application"]] = relationship(
        "Application",
        foreign_keys="Application.current_stage_id",
        back_populates="current_stage_rel",
    )

    def __repr__(self) -> str:
        return f"<WorkflowStage(code='{self.stage_code}', name='{self.stage_name}')>"

