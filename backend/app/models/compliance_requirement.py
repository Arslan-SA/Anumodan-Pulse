"""
AICTE FlowOps — ComplianceRequirement Model

Defines a configurable regulatory compliance requirement (e.g. Land Documents,
Faculty Undertaking, Financial Audit). Allows administrative configuration
without hardcoded regulatory rules.
"""

from datetime import datetime
from typing import List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ComplianceRequirement(Base):
    __tablename__ = "compliance_requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    compliance_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    application_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allowed_document_types: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    default_due_period_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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

    def __repr__(self) -> str:
        return f"<ComplianceRequirement(name='{self.name}', type='{self.compliance_type}', active={self.is_active})>"
