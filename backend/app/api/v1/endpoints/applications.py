"""
AICTE FlowOps — Application Management Endpoints

Handles:
- POST   /api/v1/applications                (Institution user create draft)
- GET    /api/v1/applications                (Role-scoped list applications with pagination & filters)
- GET    /api/v1/applications/{id}           (Role-scoped get application details)
- PATCH  /api/v1/applications/{id}           (Institution user update draft)
- POST   /api/v1/applications/{id}/submit    (Institution user submit draft)
- DELETE /api/v1/applications/{id}           (Institution user delete draft)
"""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_institution_user
from app.database import get_db
from app.models.enums import ApplicationStatus
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetailResponse,
    ApplicationResponse,
    ApplicationUpdate,
)
from app.schemas.common import PaginatedResponse
from app.schemas.institution import InstitutionResponse
from app.services.application_service import ApplicationService

router = APIRouter()


def _to_application_response(app) -> ApplicationResponse:
    """Helper to map Application model to ApplicationResponse with institution metadata."""
    return ApplicationResponse(
        id=app.id,
        application_number=app.application_number,
        institution_id=app.institution_id,
        institution_name=app.institution.institution_name if app.institution else None,
        institution_code=app.institution.institution_code if app.institution else None,
        application_type=app.application_type,
        academic_year=app.academic_year,
        status=app.status,
        current_stage=app.current_stage,
        submitted_at=app.submitted_at,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Draft Application",
    description="Creates a new application in DRAFT status for the authenticated institution.",
)
def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(require_institution_user),
    db: Session = Depends(get_db),
):
    app = ApplicationService.create_draft_application(db, current_user, payload)
    return _to_application_response(app)


@router.get(
    "",
    response_model=PaginatedResponse[ApplicationResponse],
    summary="List Applications",
    description=(
        "Returns applications scoped by role: Institution users see only their own institution's "
        "applications; Officials and Admins see cross-institutional applications. Reviewers see assigned only."
    ),
)
def list_applications(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[ApplicationStatus] = Query(None, description="Filter by application status"),
    application_type: Optional[str] = Query(None, description="Filter by application type"),
    academic_year: Optional[str] = Query(None, description="Filter by academic year"),
    search: Optional[str] = Query(None, description="Search by application number or institution name"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    items, total, total_pages = ApplicationService.list_applications_for_user(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
        status_filter=status,
        application_type=application_type,
        academic_year=academic_year,
        search=search,
    )

    return PaginatedResponse(
        items=[_to_application_response(app) for app in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    summary="Get Application Details",
    description="Retrieve details for an application. Institution users can only view their own institution's records.",
)
def get_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    app = ApplicationService.get_application_for_user(db, application_id, current_user)
    return ApplicationDetailResponse(
        id=app.id,
        application_number=app.application_number,
        institution_id=app.institution_id,
        institution_name=app.institution.institution_name if app.institution else None,
        institution_code=app.institution.institution_code if app.institution else None,
        application_type=app.application_type,
        academic_year=app.academic_year,
        status=app.status,
        current_stage=app.current_stage,
        submitted_at=app.submitted_at,
        created_at=app.created_at,
        updated_at=app.updated_at,
        institution=InstitutionResponse.model_validate(app.institution) if app.institution else None,
    )


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Update Draft Application",
    description="Update an application draft. Only permitted for the owning institution while in DRAFT status.",
)
def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    current_user: User = Depends(require_institution_user),
    db: Session = Depends(get_db),
):
    app = ApplicationService.update_draft_application(db, application_id, current_user, payload)
    return _to_application_response(app)


@router.post(
    "/{application_id}/submit",
    response_model=ApplicationResponse,
    summary="Submit Draft Application",
    description="Transitions a DRAFT application to SUBMITTED status and records submitted_at timestamp.",
)
def submit_application(
    application_id: uuid.UUID,
    current_user: User = Depends(require_institution_user),
    db: Session = Depends(get_db),
):
    app = ApplicationService.submit_draft_application(db, application_id, current_user)
    return _to_application_response(app)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Draft Application",
    description="Deletes an application draft. Submitted or in-progress applications cannot be deleted.",
)
def delete_application(
    application_id: uuid.UUID,
    current_user: User = Depends(require_institution_user),
    db: Session = Depends(get_db),
):
    ApplicationService.delete_draft_application(db, application_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
