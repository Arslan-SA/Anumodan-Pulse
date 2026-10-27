"""
AICTE FlowOps — Document Schemas

Request and response models for document metadata, uploads, and expiry tracking.
Storage keys, local paths, and storage credentials are never exposed in responses.
"""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Sanitized metadata representation of an uploaded document."""
    id: uuid.UUID
    institution_id: uuid.UUID
    application_id: Optional[uuid.UUID] = None
    compliance_record_id: Optional[uuid.UUID] = None
    document_name: str
    document_type: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by_user_id: Optional[uuid.UUID] = None
    uploaded_at: datetime
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(DocumentResponse):
    """Extended document metadata including related entity summaries."""
    institution_name: Optional[str] = None
    application_number: Optional[str] = None
    compliance_title: Optional[str] = None


class DocumentExpiringResponse(BaseModel):
    """Document expiry projection for compliance tracking."""
    id: uuid.UUID
    document_name: str
    document_type: str
    institution_id: uuid.UUID
    institution_name: Optional[str] = None
    expires_at: datetime
    days_until_expiry: int
    application_id: Optional[uuid.UUID] = None
    application_number: Optional[str] = None
    compliance_record_id: Optional[uuid.UUID] = None
    compliance_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
