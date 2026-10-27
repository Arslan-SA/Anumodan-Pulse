"""
AICTE FlowOps — WorkflowStage Model

Represents a configurable stage in an approval workflow (e.g. Scrutiny, EVC, Committee Review).
Decoupled and extensible without hardcoded transitions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.stage_history import ApplicationStageHistory


class WorkflowStage(Base):
    __tablename__ = "workflow_stages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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
    stage_histories: Mapped[List["ApplicationStageHistory"]] = relationship(
        "ApplicationStageHistory",
        back_populates="workflow_stage",
    )

    def __repr__(self) -> str:
        return f"<WorkflowStage(code='{self.stage_code}', name='{self.stage_name}')>"
