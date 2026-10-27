"""
AICTE FlowOps — Workflow Endpoints

Exposes APIs for:
- Listing and inspecting configurable workflow definitions, stages, and transitions
- Admin-driven workflow configuration and validation
- Application workflow state inspection and available action discovery
- Executing atomic workflow actions with row locking and audit trail preservation
"""

from typing import List
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    require_admin,
    require_roles,
)
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.workflow import (
    ApplicationWorkflowStateResponse,
    WorkflowActionRequest,
    WorkflowDefinitionCreate,
    WorkflowDefinitionDetailResponse,
    WorkflowDefinitionResponse,
    WorkflowDefinitionUpdate,
    WorkflowStageCreate,
    WorkflowStageResponse,
    WorkflowTransitionCreate,
    WorkflowTransitionResponse,
    WorkflowTransitionUpdate,
)
from app.services.workflow_service import WorkflowService

router = APIRouter()


# ── Workflow Definitions & Inspection ────────────────────────────────
@router.get(
    "",
    response_model=List[WorkflowDefinitionResponse],
    summary="List Active Workflows",
    description="Retrieve all active workflow definitions with stage and transition counts.",
)
def list_workflows(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.AICTE_OFFICIAL)),
    db: Session = Depends(get_db),
):
    return WorkflowService.list_active_workflow_definitions(db)


@router.get(
    "/{workflow_id}",
    response_model=WorkflowDefinitionDetailResponse,
    summary="Get Workflow Details",
    description="Retrieve details of a workflow definition including all stages and valid transitions.",
)
def get_workflow_detail(
    workflow_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.AICTE_OFFICIAL)),
    db: Session = Depends(get_db),
):
    return WorkflowService.get_workflow_definition_detail(db, workflow_id)


# ── Workflow Configuration (Admin Only) ──────────────────────────────
@router.post(
    "",
    response_model=WorkflowDefinitionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Workflow Definition",
    description="Configure a new workflow definition for a specific application type. Admin only.",
)
def create_workflow(
    payload: WorkflowDefinitionCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    wf = WorkflowService.create_workflow_definition(db, payload)
    return WorkflowService.get_workflow_definition_detail(db, wf.id)


@router.patch(
    "/{workflow_id}",
    response_model=WorkflowDefinitionDetailResponse,
    summary="Update Workflow Definition",
    description="Update workflow definition metadata. Admin only.",
)
def update_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowDefinitionUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    WorkflowService.update_workflow_definition(db, workflow_id, payload)
    return WorkflowService.get_workflow_definition_detail(db, workflow_id)


@router.post(
    "/{workflow_id}/stages",
    response_model=WorkflowStageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Stage to Workflow",
    description="Add a new approval stage to an existing workflow definition. Admin only.",
)
def add_workflow_stage(
    workflow_id: uuid.UUID,
    payload: WorkflowStageCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stage = WorkflowService.add_workflow_stage(db, workflow_id, payload)
    return WorkflowStageResponse.model_validate(stage)


@router.post(
    "/{workflow_id}/transitions",
    response_model=WorkflowTransitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Configure Workflow Transition",
    description="Configure a valid stage transition with RBAC roles and remarks requirements. Admin only.",
)
def create_workflow_transition(
    workflow_id: uuid.UUID,
    payload: WorkflowTransitionCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    transition = WorkflowService.create_workflow_transition(db, workflow_id, payload)
    return WorkflowTransitionResponse(
        id=transition.id,
        workflow_definition_id=transition.workflow_definition_id,
        from_stage_id=transition.from_stage_id,
        to_stage_id=transition.to_stage_id,
        action_name=transition.action_name,
        allowed_roles=transition.allowed_roles,
        requires_remarks=transition.requires_remarks,
        resulting_status=transition.resulting_status,
        is_active=transition.is_active,
        from_stage_name=transition.from_stage.stage_name if transition.from_stage else None,
        to_stage_name=transition.to_stage.stage_name if transition.to_stage else None,
        created_at=transition.created_at,
    )


@router.patch(
    "/{workflow_id}/transitions/{transition_id}",
    response_model=WorkflowTransitionResponse,
    summary="Update Workflow Transition",
    description="Update a transition configuration. Admin only.",
)
def update_workflow_transition(
    workflow_id: uuid.UUID,
    transition_id: uuid.UUID,
    payload: WorkflowTransitionUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    transition = WorkflowService.update_workflow_transition(
        db, workflow_id, transition_id, payload
    )
    return WorkflowTransitionResponse(
        id=transition.id,
        workflow_definition_id=transition.workflow_definition_id,
        from_stage_id=transition.from_stage_id,
        to_stage_id=transition.to_stage_id,
        action_name=transition.action_name,
        allowed_roles=transition.allowed_roles,
        requires_remarks=transition.requires_remarks,
        resulting_status=transition.resulting_status,
        is_active=transition.is_active,
        from_stage_name=transition.from_stage.stage_name if transition.from_stage else None,
        to_stage_name=transition.to_stage.stage_name if transition.to_stage else None,
        created_at=transition.created_at,
    )


# ── Application Workflow State & Execution (Workflow Router Aliases) ───
@router.get(
    "/applications/{application_id}/workflow",
    response_model=ApplicationWorkflowStateResponse,
    summary="Get Application Workflow State (Workflow Route)",
    description="Retrieve the workflow state, timeline history, and permitted actions for an application.",
)
def get_application_workflow(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return WorkflowService.get_application_workflow_state(db, application_id, current_user)


@router.post(
    "/applications/{application_id}/workflow-actions",
    response_model=ApplicationWorkflowStateResponse,
    summary="Execute Workflow Action (Workflow Route)",
    description="Execute an authorized transition on an application.",
)
def execute_workflow_action(
    application_id: uuid.UUID,
    payload: WorkflowActionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return WorkflowService.execute_workflow_action(
        db=db,
        application_id=application_id,
        user=current_user,
        payload=payload,
    )
