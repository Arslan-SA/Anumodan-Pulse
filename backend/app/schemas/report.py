"""
AICTE FlowOps — Report Schemas

Schemas for generating, tabulating, and exporting system reports:
applications, compliance, overdue items, and document expiries.
"""

from datetime import date, datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict


class ApplicationReportRow(BaseModel):
    """Detailed row for application reports."""
    id: uuid.UUID
    application_number: str
    institution_id: uuid.UUID
    institution_code: Optional[str] = None
    institution_name: Optional[str] = None
    application_type: str
    academic_year: str
    status: str
    current_stage: Optional[str] = None
    submitted_at: Optional[datetime] = None
    days_pending: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplianceReportRow(BaseModel):
    """Detailed row for compliance reports."""
    id: uuid.UUID
    institution_id: uuid.UUID
    institution_name: Optional[str] = None
    application_id: Optional[uuid.UUID] = None
    application_number: Optional[str] = None
    compliance_type: str
    title: str
    status: str
    due_date: Optional[date] = None
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    is_overdue: bool = False

    model_config = ConfigDict(from_attributes=True)


class OverdueReportRow(BaseModel):
    """Detailed row for overdue monitoring reports."""
    entity_type: str
    entity_id: uuid.UUID
    reference_number: str
    institution_name: Optional[str] = None
    current_status: str
    target_date: Optional[str] = None
    days_overdue: int = 0
    remarks: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentReportRow(BaseModel):
    """Detailed row for document expiry reports."""
    id: uuid.UUID
    document_name: str
    document_type: str
    institution_id: uuid.UUID
    institution_name: Optional[str] = None
    application_id: Optional[uuid.UUID] = None
    application_number: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_at: datetime
    expires_at: Optional[datetime] = None
    expiry_status: str

    model_config = ConfigDict(from_attributes=True)
