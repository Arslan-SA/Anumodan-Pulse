"""
AICTE FlowOps — Document Management Endpoints

Handles:
- POST   /api/v1/documents                  (Upload document)
- GET    /api/v1/documents/expiring         (Query expiring documents)
- GET    /api/v1/documents/{id}             (Retrieve metadata)
- GET    /api/v1/documents/{id}/download    (Authorized download)
- DELETE /api/v1/documents/{id}             (Delete document)
"""

from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentExpiringResponse,
    DocumentResponse,
)
from app.services.document_service import DocumentService

router = APIRouter()


def _to_document_detail_response(doc) -> DocumentDetailResponse:
    return DocumentDetailResponse(
        id=doc.id,
        institution_id=doc.institution_id,
        institution_name=doc.institution.institution_name if doc.institution else None,
        application_id=doc.application_id,
        application_number=doc.application.application_number if doc.application else None,
        compliance_record_id=doc.compliance_record_id,
        compliance_title=doc.compliance_record.title if doc.compliance_record else None,
        document_name=doc.document_name,
        document_type=doc.document_type,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        uploaded_by_user_id=doc.uploaded_by_user_id,
        uploaded_at=doc.uploaded_at,
        expires_at=doc.expires_at,
    )


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Document",
)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    document_name: str = Form(..., min_length=2, max_length=255, description="Document display name"),
    document_type: str = Form(..., min_length=2, max_length=100, description="Statutory document category"),
    application_id: Optional[uuid.UUID] = Form(None, description="Optional linked application ID"),
    compliance_record_id: Optional[uuid.UUID] = Form(None, description="Optional linked compliance record ID"),
    expires_at: Optional[datetime] = Form(None, description="Optional document expiry timestamp"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload and register a document with strict institutional boundary checks.
    Validates file extension, size limit, and genuine magic-byte signatures.
    """
    doc = await DocumentService.upload_document(
        db=db,
        user=current_user,
        file=file,
        document_name=document_name,
        document_type=document_type,
        application_id=application_id,
        compliance_record_id=compliance_record_id,
        expires_at=expires_at,
    )
    return doc


@router.get(
    "/expiring",
    response_model=List[DocumentExpiringResponse],
    summary="List Expiring Documents",
)
def list_expiring_documents(
    days_window: int = Query(30, ge=1, le=365, description="Lookahead window in days (default: 30)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve documents expiring within the configured window.
    Institutions see only their own documents; officials see cross-institution records.
    """
    return DocumentService.list_expiring_documents(
        db=db,
        user=current_user,
        days_window=days_window,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get Document Metadata",
)
def get_document_metadata(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve sanitized document metadata.
    Enforces institutional data isolation. Never leaks storage keys or server paths.
    """
    doc = DocumentService.get_document_metadata(db, document_id, current_user)
    return _to_document_detail_response(doc)


@router.get(
    "/{document_id}/download",
    summary="Download Document",
)
def download_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Authorize and download a document.
    Serves local file securely or redirects to temporary signed URL.
    """
    return DocumentService.download_document(db, document_id, current_user)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Document",
)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a document from storage and metadata records.
    Permitted only for the owning institution (or admin) and only if not part of a VERIFIED record.
    """
    DocumentService.delete_document(db, document_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
