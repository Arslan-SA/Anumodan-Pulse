"""
AICTE FlowOps — ComplianceRequirement Schemas

Request and response models for configurable compliance requirements.
"""

from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ComplianceRequirementCreate(BaseModel):
    """Admin payload to define a new configurable regulatory requirement."""
    name: str = Field(..., min_length=2, max_length=255, description="Requirement title")
    compliance_type: str = Field(..., min_length=2, max_length=100, description="Category / undertaking type")
    description: Optional[str] = Field(None, description="Detailed statutory description")
    application_type: Optional[str] = Field(None, max_length=100, description="Applicable application type or null for all")
    is_required: bool = Field(True, description="Whether this compliance is mandatory")
    allowed_document_types: List[str] = Field(
        default_factory=list,
        description="List of acceptable document types (e.g. ['Land Registry', 'Building Plan'])"
    )
    default_due_period_days: Optional[int] = Field(None, ge=1, le=365, description="Default submission window in days")
    is_active: bool = Field(True, description="Whether this requirement is currently enforced")


class ComplianceRequirementUpdate(BaseModel):
    """Admin payload to modify requirement parameters without rewriting existing records."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    compliance_type: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    application_type: Optional[str] = Field(None, max_length=100)
    is_required: Optional[bool] = None
    allowed_document_types: Optional[List[str]] = None
    default_due_period_days: Optional[int] = Field(None, ge=1, le=365)
    is_active: Optional[bool] = None


class ComplianceRequirementStatusUpdate(BaseModel):
    """Admin payload to activate or deactivate a requirement."""
    is_active: bool = Field(..., description="Active status of the requirement")


class ComplianceRequirementResponse(BaseModel):
    """Public schema for a compliance requirement."""
    id: uuid.UUID
    name: str
    compliance_type: str
    description: Optional[str] = None
    application_type: Optional[str] = None
    is_required: bool
    allowed_document_types: List[str] = Field(default_factory=list)
    default_due_period_days: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
