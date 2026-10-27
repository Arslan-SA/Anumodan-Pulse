"""
AICTE FlowOps — Institution Management Endpoints

Handles:
- GET   /api/v1/institutions/me         (Institution user view own profile)
- PATCH /api/v1/institutions/me         (Institution user update permitted profile fields)
- GET   /api/v1/institutions            (Admin & Officials list institutions with pagination & filters)
- GET   /api/v1/institutions/{id}       (Admin & Officials get institution details)
"""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_institution_user, require_roles
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.institution import InstitutionResponse, InstitutionUpdate
from app.services.institution_service import InstitutionService

router = APIRouter()


@router.get(
    "/me",
    response_model=InstitutionResponse,
    summary="Get Own Institution Profile",
    description="Returns the technical institution associated with the authenticated institution user.",
)
def get_my_institution(
    current_user: User = Depends(require_institution_user),
    db: Session = Depends(get_db),
):
    return InstitutionService.get_user_institution(db, current_user)


@router.patch(
    "/me",
    response_model=InstitutionResponse,
    summary="Update Own Institution Profile",
    description="Update permitted institution details (address, contact, type). Institution ID and Code cannot be modified.",
)
def update_my_institution(
    payload: InstitutionUpdate,
    current_user: User = Depends(require_institution_user),
    db: Session = Depends(get_db),
):
    return InstitutionService.update_user_institution(db, current_user, payload)


@router.get(
    "",
    response_model=PaginatedResponse[InstitutionResponse],
    summary="List Institutions (Admin / Official)",
    description="Paginated list of technical institutions with name/code search and state filter.",
)
def list_institutions(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by institution name or code"),
    state: Optional[str] = Query(None, description="Filter by state"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.AICTE_OFFICIAL)),
    db: Session = Depends(get_db),
):
    items, total, total_pages = InstitutionService.list_institutions(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        state=state,
    )
    return PaginatedResponse(
        items=[InstitutionResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Get Institution By ID (Admin / Official)",
    description="Retrieve full details for any technical institution.",
)
def get_institution_by_id(
    institution_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.AICTE_OFFICIAL)),
    db: Session = Depends(get_db),
):
    return InstitutionService.get_institution_by_id(db, institution_id)
