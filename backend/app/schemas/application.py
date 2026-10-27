"""
AICTE FlowOps — Application Schemas

Request and response models for approval applications.
"""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApplicationStatus
from app.schemas.institution import InstitutionResponse


class ApplicationCreate(BaseModel):
    """
    Client payload to create a new draft application.
    Server strictly controls institution_id, status, current_stage, and application_number.
    """
    application_type: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Type of approval sought (e.g. Extension of Approval, New Course, Intake Increase)",
    )
    academic_year: str = Field(
        ...,
        min_length=4,
        max_length=20,
        description="Statutory academic session (e.g. 2026-2027)",
    )


class ApplicationUpdate(BaseModel):
    """Permitted edits for applications still in DRAFT status."""
    application_type: Optional[str] = Field(None, min_length=2, max_length=100)
    academic_year: Optional[str] = Field(None, min_length=4, max_length=20)


class ApplicationResponse(BaseModel):
    """Public representation of an approval application."""
    id: uuid.UUID
    application_number: str
    institution_id: uuid.UUID
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    application_type: str
    academic_year: str
    status: ApplicationStatus
    current_stage: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationDetailResponse(ApplicationResponse):
    """Detailed application view including full institutional profile."""
    institution: Optional[InstitutionResponse] = None
