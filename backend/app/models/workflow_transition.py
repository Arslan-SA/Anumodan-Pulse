"""
AICTE FlowOps — WorkflowTransition Model

Defines a permitted stage transition within a workflow definition,
enforcing RBAC, conditionality, and remarks validation.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.workflow_definition import WorkflowDefinition
    from app.models.workflow_stage import WorkflowStage


class WorkflowTransition(Base):
    __tablename__ = "workflow_transitions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_stage_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_stages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    to_stage_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_stages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    allowed_roles: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    requires_remarks: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    resulting_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ───────────────────────────────────────────────────
    workflow_definition: Mapped["WorkflowDefinition"] = relationship(
        "WorkflowDefinition",
        back_populates="transitions",
    )
    from_stage: Mapped[Optional["WorkflowStage"]] = relationship(
        "WorkflowStage",
        foreign_keys=[from_stage_id],
        back_populates="outgoing_transitions",
    )
    to_stage: Mapped["WorkflowStage"] = relationship(
        "WorkflowStage",
        foreign_keys=[to_stage_id],
        back_populates="incoming_transitions",
    )

    def __repr__(self) -> str:
        return f"<WorkflowTransition(action='{self.action_name}', from='{self.from_stage_id}', to='{self.to_stage_id}')>"
