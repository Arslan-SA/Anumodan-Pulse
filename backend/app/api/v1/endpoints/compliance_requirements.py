"""
AICTE FlowOps — Compliance Requirements Configuration Endpoints

Administrative endpoints to manage configurable regulatory requirements:
- GET    /api/v1/compliance-requirements
- POST   /api/v1/compliance-requirements
- PATCH  /api/v1/compliance-requirements/{id}
- PATCH  /api/v1/compliance-requirements/{id}/status
"""

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_admin
from app.database import get_db
from app.models.user import User
from app.schemas.compliance_requirement import (
    ComplianceRequirementCreate,
    ComplianceRequirementResponse,
    ComplianceRequirementStatusUpdate,
    ComplianceRequirementUpdate,
)
from app.services.compliance_service import ComplianceService

router = APIRouter()


@router.get(
    "",
    response_model=List[ComplianceRequirementResponse],
    summary="List Compliance Requirements",
)
def list_requirements(
    active_only: bool = Query(False, description="Filter only active requirements"),
    application_type: Optional[str] = Query(None, description="Filter by application type"),
    compliance_type: Optional[str] = Query(None, description="Filter by compliance type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List configured compliance requirements and undertaking rules.
    Open to all authenticated users so institutions can view statutory requirements.
    """
    return ComplianceService.list_requirements(
        db=db,
        active_only=active_only,
        application_type=application_type,
        compliance_type=compliance_type,
    )


@router.post(
    "",
    response_model=ComplianceRequirementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Compliance Requirement",
)
def create_requirement(
    payload: ComplianceRequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Configure a new compliance requirement.
    Restricted to system administrators.
    """
    return ComplianceService.create_requirement(db, current_user, payload)


@router.patch(
    "/{requirement_id}",
    response_model=ComplianceRequirementResponse,
    summary="Update Compliance Requirement",
)
def update_requirement(
    requirement_id: uuid.UUID,
    payload: ComplianceRequirementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update requirement parameters (does not rewrite existing historical records).
    Restricted to system administrators.
    """
    return ComplianceService.update_requirement(db, current_user, requirement_id, payload)


@router.patch(
    "/{requirement_id}/status",
    response_model=ComplianceRequirementResponse,
    summary="Update Compliance Requirement Status",
)
def update_requirement_status(
    requirement_id: uuid.UUID,
    payload: ComplianceRequirementStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Activate or deactivate a compliance requirement.
    Restricted to system administrators.
    """
    return ComplianceService.update_requirement_status(db, current_user, requirement_id, payload.is_active)
