"""
AICTE FlowOps — ApplicationStageHistory Model

Represents the chronological record of stage movements and decisions for an application.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.workflow_stage import WorkflowStage
    from app.models.user import User


class ApplicationStageHistory(Base):
    __tablename__ = "application_stage_histories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    workflow_stage_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_stages.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acted_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    exited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ───────────────────────────────────────────────────
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="stage_histories",
    )
    workflow_stage: Mapped["WorkflowStage"] = relationship(
        "WorkflowStage",
        back_populates="stage_histories",
    )
    acted_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="stage_actions",
    )

    def __repr__(self) -> str:
        return f"<ApplicationStageHistory(app_id='{self.application_id}', status='{self.status}')>"
