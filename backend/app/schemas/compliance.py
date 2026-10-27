"""
AICTE FlowOps — Compliance Schemas

Request and response models for compliance records, undertakings,
verification workflows, and audit history.
"""

from datetime import date, datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ComplianceStatus
from app.schemas.document import DocumentResponse


class ComplianceRecordCreate(BaseModel):
    """
    Institution payload to create a new compliance or undertaking record.
    The server associates the institution from the authenticated user.
    Status defaults to PENDING. Verification fields cannot be set by client.
    """
    compliance_type: str = Field(..., min_length=2, max_length=100, description="Compliance category")
    title: str = Field(..., min_length=2, max_length=255, description="Short title of statutory undertaking")
    description: Optional[str] = Field(None, description="Detailed undertaking or explanation")
    due_date: Optional[date] = Field(None, description="Statutory compliance due date")
    application_id: Optional[uuid.UUID] = Field(None, description="Optional associated application ID")


class ComplianceRecordUpdate(BaseModel):
    """
    Permitted modifications to a compliance record while in PENDING or REJECTED status.
    Institution ownership, status, and verification fields cannot be modified here.
    """
    compliance_type: Optional[str] = Field(None, min_length=2, max_length=100)
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    due_date: Optional[date] = None
    application_id: Optional[uuid.UUID] = None


class ComplianceVerifyRequest(BaseModel):
    """Optional official remarks when verifying a compliance record."""
    remarks: Optional[str] = Field(None, max_length=1000, description="Verification remarks or notes")


class ComplianceRejectRequest(BaseModel):
    """Mandatory official rejection payload."""
    reason: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Statutory rejection reason explaining deficiencies",
    )


class ComplianceHistoryResponse(BaseModel):
    """Public representation of a compliance audit action."""
    id: uuid.UUID
    compliance_record_id: uuid.UUID
    action: str
    from_status: Optional[str] = None
    to_status: str
    remarks: Optional[str] = None
    acted_by_user_id: Optional[uuid.UUID] = None
    acted_by_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplianceRecordResponse(BaseModel):
    """Standard representation of a compliance record."""
    id: uuid.UUID
    institution_id: uuid.UUID
    institution_name: Optional[str] = None
    application_id: Optional[uuid.UUID] = None
    application_number: Optional[str] = None
    compliance_type: str
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: ComplianceStatus
    rejection_reason: Optional[str] = None
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verified_by_user_id: Optional[uuid.UUID] = None
    verified_by_name: Optional[str] = None
    document_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplianceRecordDetailResponse(ComplianceRecordResponse):
    """Detailed compliance representation including documents and audit history."""
    documents: List[DocumentResponse] = Field(default_factory=list)
    histories: List[ComplianceHistoryResponse] = Field(default_factory=list)
