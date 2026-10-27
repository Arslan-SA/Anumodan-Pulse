"""
AICTE FlowOps — Compliance Endpoints

Handles statutory compliance records and undertakings:
- POST   /api/v1/compliance                 (Institution user create record)
- GET    /api/v1/compliance                 (List records with role-based scoping)
- GET    /api/v1/compliance/{id}            (Get record details with docs and history)
- PATCH  /api/v1/compliance/{id}            (Institution user update record)
- POST   /api/v1/compliance/{id}/submit     (Institution user submit record)
- POST   /api/v1/compliance/{id}/verify     (Official verify submission)
- POST   /api/v1/compliance/{id}/reject     (Official reject submission)
"""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_official_or_admin
from app.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.compliance import (
    ComplianceHistoryResponse,
    ComplianceRecordCreate,
    ComplianceRecordDetailResponse,
    ComplianceRecordResponse,
    ComplianceRecordUpdate,
    ComplianceRejectRequest,
    ComplianceVerifyRequest,
)
from app.schemas.document import DocumentResponse
from app.services.compliance_service import ComplianceService

router = APIRouter()


def _to_compliance_response(rec) -> ComplianceRecordResponse:
    return ComplianceRecordResponse(
        id=rec.id,
        institution_id=rec.institution_id,
        institution_name=rec.institution.institution_name if rec.institution else None,
        application_id=rec.application_id,
        application_number=rec.application.application_number if rec.application else None,
        compliance_type=rec.compliance_type,
        title=rec.title,
        description=rec.description,
        due_date=rec.due_date,
        status=rec.status,
        rejection_reason=rec.rejection_reason,
        submitted_at=rec.submitted_at,
        verified_at=rec.verified_at,
        verified_by_user_id=rec.verified_by_user_id,
        verified_by_name=rec.verified_by_user.full_name if rec.verified_by_user else None,
        document_count=len(rec.documents) if rec.documents else 0,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
    )


def _to_compliance_detail_response(rec) -> ComplianceRecordDetailResponse:
    base = _to_compliance_response(rec)
    docs = [
        DocumentResponse(
            id=d.id,
            institution_id=d.institution_id,
            application_id=d.application_id,
            compliance_record_id=d.compliance_record_id,
            document_name=d.document_name,
            document_type=d.document_type,
            mime_type=d.mime_type,
            file_size=d.file_size,
            uploaded_by_user_id=d.uploaded_by_user_id,
            uploaded_at=d.uploaded_at,
            expires_at=d.expires_at,
        )
        for d in (rec.documents or [])
    ]
    histories = [
        ComplianceHistoryResponse(
            id=h.id,
            compliance_record_id=h.compliance_record_id,
            action=h.action,
            from_status=h.from_status,
            to_status=h.to_status,
            remarks=h.remarks,
            acted_by_user_id=h.acted_by_user_id,
            acted_by_name=h.acted_by_user.full_name if h.acted_by_user else None,
            created_at=h.created_at,
        )
        for h in (rec.histories or [])
    ]
    return ComplianceRecordDetailResponse(
        **base.model_dump(),
        documents=docs,
        histories=histories,
    )


@router.post(
    "",
    response_model=ComplianceRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Compliance Record",
)
def create_compliance_record(
    payload: ComplianceRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new compliance record or statutory undertaking.
    Strictly restricted to INSTITUTION_USER; automatically linked to their institution.
    """
    record = ComplianceService.create_compliance_record(db, current_user, payload)
    return _to_compliance_response(record)


@router.get(
    "",
    response_model=PaginatedResponse[ComplianceRecordResponse],
    summary="List Compliance Records",
)
def list_compliance_records(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, SUBMITTED, VERIFIED, REJECTED)"),
    compliance_type: Optional[str] = Query(None, description="Filter by compliance type"),
    institution_id: Optional[uuid.UUID] = Query(None, description="Filter by institution (Officials only)"),
    application_id: Optional[uuid.UUID] = Query(None, description="Filter by application"),
    search: Optional[str] = Query(None, description="Search in title or description"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List compliance records with role-based scoping:
    - INSTITUTION_USER: Only records belonging to their affiliated institution
    - ADMIN / AICTE_OFFICIAL: All records across institutions with flexible filters
    - REVIEWER: Only assigned records (empty if unassigned)
    """
    records, total, curr_page, limit, total_pages = ComplianceService.list_compliance_records(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
        status_filter=status,
        compliance_type=compliance_type,
        institution_id=institution_id,
        application_id=application_id,
        search=search,
    )
    return PaginatedResponse(
        items=[_to_compliance_response(r) for r in records],
        total=total,
        page=curr_page,
        page_size=limit,
        total_pages=total_pages,
    )


@router.get(
    "/{compliance_id}",
    response_model=ComplianceRecordDetailResponse,
    summary="Get Compliance Record Details",
)
def get_compliance_record(
    compliance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve compliance record with full document metadata and audit verification history.
    Enforces institutional isolation.
    """
    record = ComplianceService.get_compliance_record(db, compliance_id, current_user)
    return _to_compliance_detail_response(record)


@router.patch(
    "/{compliance_id}",
    response_model=ComplianceRecordResponse,
    summary="Update Compliance Record",
)
def update_compliance_record(
    compliance_id: uuid.UUID,
    payload: ComplianceRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update permitted fields of a compliance record.
    Allowed only for owning institution user while record is in PENDING or REJECTED status.
    """
    record = ComplianceService.update_compliance_record(db, compliance_id, current_user, payload)
    return _to_compliance_response(record)


@router.post(
    "/{compliance_id}/submit",
    response_model=ComplianceRecordResponse,
    summary="Submit Compliance Record",
)
def submit_compliance_record(
    compliance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Submit a compliance record for statutory verification.
    Validates configurable requirements (e.g., mandatory supporting documents).
    """
    record = ComplianceService.submit_compliance_record(db, compliance_id, current_user)
    return _to_compliance_response(record)


@router.post(
    "/{compliance_id}/verify",
    response_model=ComplianceRecordResponse,
    summary="Verify Compliance Submission",
)
def verify_compliance_record(
    compliance_id: uuid.UUID,
    payload: Optional[ComplianceVerifyRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official_or_admin),
):
    """
    Statutorily verify a compliance record.
    Restricted to AICTE officials and administrators.
    Preserves audit history. Does not automatically approve an application.
    """
    remarks = payload.remarks if payload else None
    record = ComplianceService.verify_compliance_record(db, compliance_id, current_user, remarks)
    return _to_compliance_response(record)


@router.post(
    "/{compliance_id}/reject",
    response_model=ComplianceRecordResponse,
    summary="Reject Compliance Submission",
)
def reject_compliance_record(
    compliance_id: uuid.UUID,
    payload: ComplianceRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_official_or_admin),
):
    """
    Reject a compliance record with a mandatory statutory reason.
    Restricted to AICTE officials and administrators.
    Allows the institution to address deficiencies and resubmit.
    """
    record = ComplianceService.reject_compliance_record(db, compliance_id, current_user, payload.reason)
    return _to_compliance_response(record)
