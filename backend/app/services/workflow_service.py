"""
AICTE FlowOps — Workflow Engine Service

Manages configurable workflow definitions, stage transitions, RBAC enforcement,
application state progression, row-level concurrency locking, and audit history.
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.application import Application
from app.models.enums import ApplicationStatus, UserRole
from app.models.stage_history import ApplicationStageHistory
from app.models.user import User
from app.models.workflow_definition import WorkflowDefinition
from app.models.workflow_stage import WorkflowStage
from app.models.workflow_transition import WorkflowTransition
from app.schemas.workflow import (
    ApplicationWorkflowStateResponse,
    AvailableActionResponse,
    StageHistoryItemResponse,
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

# Standard mapping of workflow actions to application lifecycle statuses
STATUS_ACTION_MAP = {
    "START_SCRUTINY": ApplicationStatus.UNDER_SCRUTINY,
    "COMPLETE_SCRUTINY": ApplicationStatus.UNDER_SCRUTINY,
    "RETURN_FOR_CLARIFICATION": ApplicationStatus.RETURNED_FOR_CLARIFICATION,
    "RESUBMIT_CLARIFICATION": ApplicationStatus.UNDER_SCRUTINY,
    "SCHEDULE_EVC": ApplicationStatus.EVC_SCHEDULED,
    "COMPLETE_EVC": ApplicationStatus.UNDER_REVIEW,
    "FORWARD_FOR_REVIEW": ApplicationStatus.UNDER_REVIEW,
    "COMPLETE_REVIEW": ApplicationStatus.UNDER_REVIEW,
    "RECORD_DECISION": ApplicationStatus.APPROVED,
    "CLOSE_APPLICATION": ApplicationStatus.CLOSED,
}


class WorkflowService:
    # ── Workflow Definitions & Admin Configuration ───────────────────

    @staticmethod
    def list_active_workflow_definitions(db: Session) -> List[WorkflowDefinitionResponse]:
        """List active workflow definitions with summary counts."""
        definitions = db.scalars(
            select(WorkflowDefinition)
            .where(WorkflowDefinition.is_active.is_(True))
            .order_by(WorkflowDefinition.name.asc())
        ).all()

        results = []
        for d in definitions:
            stages_count = db.scalar(
                select(func.count(WorkflowStage.id)).where(
                    WorkflowStage.workflow_definition_id == d.id
                )
            ) or 0
            transitions_count = db.scalar(
                select(func.count(WorkflowTransition.id)).where(
                    WorkflowTransition.workflow_definition_id == d.id
                )
            ) or 0
            results.append(
                WorkflowDefinitionResponse(
                    id=d.id,
                    name=d.name,
                    application_type=d.application_type,
                    description=d.description,
                    is_active=d.is_active,
                    stages_count=stages_count,
                    transitions_count=transitions_count,
                    created_at=d.created_at,
                    updated_at=d.updated_at,
                )
            )
        return results

    @staticmethod
    def get_workflow_definition_detail(
        db: Session, workflow_id: uuid.UUID
    ) -> WorkflowDefinitionDetailResponse:
        """Retrieve full details of a workflow definition including stages and transitions."""
        definition = db.scalar(
            select(WorkflowDefinition)
            .options(
                selectinload(WorkflowDefinition.stages),
                selectinload(WorkflowDefinition.transitions).joinedload(
                    WorkflowTransition.from_stage
                ),
                selectinload(WorkflowDefinition.transitions).joinedload(
                    WorkflowTransition.to_stage
                ),
            )
            .where(WorkflowDefinition.id == workflow_id)
        )
        if not definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow definition with ID '{workflow_id}' was not found.",
            )

        stages_resp = [
            WorkflowStageResponse(
                id=s.id,
                workflow_definition_id=s.workflow_definition_id,
                stage_name=s.stage_name,
                stage_code=s.stage_code,
                description=s.description,
                sequence_order=s.sequence_order,
                is_active=s.is_active,
                created_at=s.created_at,
            )
            for s in definition.stages
        ]

        transitions_resp = [
            WorkflowTransitionResponse(
                id=t.id,
                workflow_definition_id=t.workflow_definition_id,
                from_stage_id=t.from_stage_id,
                to_stage_id=t.to_stage_id,
                action_name=t.action_name,
                allowed_roles=t.allowed_roles,
                requires_remarks=t.requires_remarks,
                resulting_status=t.resulting_status,
                is_active=t.is_active,
                from_stage_name=t.from_stage.stage_name if t.from_stage else None,
                to_stage_name=t.to_stage.stage_name if t.to_stage else None,
                created_at=t.created_at,
            )
            for t in definition.transitions
        ]

        return WorkflowDefinitionDetailResponse(
            id=definition.id,
            name=definition.name,
            application_type=definition.application_type,
            description=definition.description,
            is_active=definition.is_active,
            stages=stages_resp,
            transitions=transitions_resp,
            created_at=definition.created_at,
            updated_at=definition.updated_at,
        )

    @staticmethod
    def create_workflow_definition(
        db: Session, payload: WorkflowDefinitionCreate
    ) -> WorkflowDefinition:
        """Create a new workflow definition (Admin only)."""
        existing = db.scalar(
            select(WorkflowDefinition).where(
                WorkflowDefinition.name == payload.name.strip(),
                WorkflowDefinition.application_type == payload.application_type.strip(),
            )
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A workflow definition for '{payload.application_type}' with name '{payload.name}' already exists.",
            )

        definition = WorkflowDefinition(
            name=payload.name.strip(),
            application_type=payload.application_type.strip(),
            description=payload.description.strip() if payload.description else None,
            is_active=payload.is_active,
        )
        db.add(definition)
        db.commit()
        db.refresh(definition)
        return definition

    @staticmethod
    def update_workflow_definition(
        db: Session, workflow_id: uuid.UUID, payload: WorkflowDefinitionUpdate
    ) -> WorkflowDefinition:
        """Update workflow definition metadata."""
        definition = db.get(WorkflowDefinition, workflow_id)
        if not definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow definition with ID '{workflow_id}' was not found.",
            )

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(definition, field, value.strip() if isinstance(value, str) else value)

        db.commit()
        db.refresh(definition)
        return definition

    @staticmethod
    def add_workflow_stage(
        db: Session, workflow_id: uuid.UUID, payload: WorkflowStageCreate
    ) -> WorkflowStage:
        """Add a stage to a workflow definition."""
        definition = db.get(WorkflowDefinition, workflow_id)
        if not definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow definition with ID '{workflow_id}' was not found.",
            )

        # Ensure stage_code is unique globally (per existing model constraint)
        existing_stage = db.scalar(
            select(WorkflowStage).where(
                WorkflowStage.stage_code == payload.stage_code.strip()
            )
        )
        if existing_stage:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A workflow stage with code '{payload.stage_code}' already exists.",
            )

        stage = WorkflowStage(
            workflow_definition_id=workflow_id,
            stage_name=payload.stage_name.strip(),
            stage_code=payload.stage_code.strip(),
            description=payload.description.strip() if payload.description else None,
            sequence_order=payload.sequence_order,
            is_active=payload.is_active,
        )
        db.add(stage)
        db.commit()
        db.refresh(stage)
        return stage

    @staticmethod
    def create_workflow_transition(
        db: Session, workflow_id: uuid.UUID, payload: WorkflowTransitionCreate
    ) -> WorkflowTransition:
        """Configure a valid transition between stages within a workflow."""
        definition = db.get(WorkflowDefinition, workflow_id)
        if not definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow definition with ID '{workflow_id}' was not found.",
            )

        # Validate to_stage belongs to this workflow
        to_stage = db.get(WorkflowStage, payload.to_stage_id)
        if not to_stage or to_stage.workflow_definition_id != workflow_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Target stage '{payload.to_stage_id}' does not belong to workflow '{workflow_id}'.",
            )

        # Validate from_stage belongs to this workflow if provided
        if payload.from_stage_id:
            from_stage = db.get(WorkflowStage, payload.from_stage_id)
            if not from_stage or from_stage.workflow_definition_id != workflow_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Source stage '{payload.from_stage_id}' does not belong to workflow '{workflow_id}'.",
                )

        # Prevent duplicate active transition for same action and source stage
        duplicate_query = select(WorkflowTransition).where(
            WorkflowTransition.workflow_definition_id == workflow_id,
            WorkflowTransition.action_name == payload.action_name.strip(),
            WorkflowTransition.is_active.is_(True),
        )
        if payload.from_stage_id is None:
            duplicate_query = duplicate_query.where(WorkflowTransition.from_stage_id.is_(None))
        else:
            duplicate_query = duplicate_query.where(
                WorkflowTransition.from_stage_id == payload.from_stage_id
            )

        if db.scalar(duplicate_query):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An active transition for action '{payload.action_name}' from the specified stage already exists.",
            )

        transition = WorkflowTransition(
            workflow_definition_id=workflow_id,
            from_stage_id=payload.from_stage_id,
            to_stage_id=payload.to_stage_id,
            action_name=payload.action_name.strip(),
            allowed_roles=[r.strip() for r in payload.allowed_roles],
            requires_remarks=payload.requires_remarks,
            resulting_status=payload.resulting_status.strip() if payload.resulting_status else None,
            is_active=payload.is_active,
        )
        db.add(transition)
        db.commit()
        db.refresh(transition)
        return transition

    @staticmethod
    def update_workflow_transition(
        db: Session,
        workflow_id: uuid.UUID,
        transition_id: uuid.UUID,
        payload: WorkflowTransitionUpdate,
    ) -> WorkflowTransition:
        """Update a transition's configuration."""
        transition = db.get(WorkflowTransition, transition_id)
        if not transition or transition.workflow_definition_id != workflow_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transition with ID '{transition_id}' was not found in this workflow.",
            )

        update_data = payload.model_dump(exclude_unset=True)
        if "from_stage_id" in update_data and update_data["from_stage_id"] is not None:
            from_stage = db.get(WorkflowStage, update_data["from_stage_id"])
            if not from_stage or from_stage.workflow_definition_id != workflow_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Source stage does not belong to this workflow definition.",
                )

        if "to_stage_id" in update_data and update_data["to_stage_id"] is not None:
            to_stage = db.get(WorkflowStage, update_data["to_stage_id"])
            if not to_stage or to_stage.workflow_definition_id != workflow_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Target stage does not belong to this workflow definition.",
                )

        for field, value in update_data.items():
            if value is not None:
                if isinstance(value, str):
                    setattr(transition, field, value.strip())
                elif isinstance(value, list):
                    setattr(transition, field, [r.strip() for r in value])
                else:
                    setattr(transition, field, value)

        db.commit()
        db.refresh(transition)
        return transition

    # ── Workflow Initialization on Application Submission ─────────────

    @staticmethod
    def initialize_application_workflow(
        db: Session,
        application: Application,
        user: User,
    ) -> Application:
        """
        Initializes an application's workflow upon submission.
        Validates that an active workflow exists, identifies the initial stage,
        updates application stage & status, and records the initial stage history.
        Must be executed within a database transaction.
        """
        # 1. Look up active workflow definition matching application_type
        workflow_def = db.scalar(
            select(WorkflowDefinition)
            .where(
                WorkflowDefinition.application_type == application.application_type,
                WorkflowDefinition.is_active.is_(True),
            )
            .order_by(WorkflowDefinition.created_at.desc())
        )
        if not workflow_def:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"No active workflow definition configured for application type '{application.application_type}'. Application cannot be submitted.",
            )

        # 2. Identify configured initial stage
        init_transition = db.scalar(
            select(WorkflowTransition)
            .where(
                WorkflowTransition.workflow_definition_id == workflow_def.id,
                WorkflowTransition.from_stage_id.is_(None),
                WorkflowTransition.is_active.is_(True),
            )
        )
        initial_stage = None
        if init_transition:
            initial_stage = db.get(WorkflowStage, init_transition.to_stage_id)

        if not initial_stage:
            # Fallback to stage with lowest sequence_order
            initial_stage = db.scalar(
                select(WorkflowStage)
                .where(
                    WorkflowStage.workflow_definition_id == workflow_def.id,
                    WorkflowStage.is_active.is_(True),
                )
                .order_by(WorkflowStage.sequence_order.asc())
            )

        if not initial_stage:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Workflow definition '{workflow_def.name}' has no active stages configured.",
            )

        # 3. Update application state
        application.workflow_definition_id = workflow_def.id
        application.current_stage_id = initial_stage.id
        application.current_stage = initial_stage.stage_name

        if init_transition and init_transition.resulting_status:
            application.status = ApplicationStatus(init_transition.resulting_status)
        else:
            application.status = ApplicationStatus.SUBMITTED

        application.submitted_at = datetime.now(timezone.utc)

        # 4. Create initial ApplicationStageHistory record
        status_str = (
            application.status.value
            if hasattr(application.status, "value")
            else str(application.status)
        )
        history = ApplicationStageHistory(
            application_id=application.id,
            workflow_stage_id=initial_stage.id,
            status=status_str,
            action_name=init_transition.action_name if init_transition else "SUBMIT",
            remarks="Application submitted and entered approval workflow.",
            acted_by_user_id=user.id,
            entered_at=datetime.now(timezone.utc),
        )
        db.add(history)
        return application

    # ── Application Workflow State & Execution ────────────────────────

    @staticmethod
    def get_application_workflow_state(
        db: Session,
        application_id: uuid.UUID,
        user: User,
    ) -> ApplicationWorkflowStateResponse:
        """
        Return the workflow state, stage history, and available actions for an application.
        Strictly enforces role-based access scoping.
        """
        app = db.scalar(
            select(Application)
            .options(
                joinedload(Application.workflow_definition),
                joinedload(Application.current_stage_rel),
            )
            .where(Application.id == application_id)
        )
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' was not found.",
            )

        # Access check
        if user.role == UserRole.INSTITUTION_USER:
            if app.institution_id != user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Application with ID '{application_id}' was not found.",
                )
        elif user.role == UserRole.REVIEWER:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' is not assigned to this reviewer.",
            )

        # Load stage histories
        histories = db.scalars(
            select(ApplicationStageHistory)
            .options(
                joinedload(ApplicationStageHistory.workflow_stage),
                joinedload(ApplicationStageHistory.acted_by_user),
            )
            .where(ApplicationStageHistory.application_id == app.id)
            .order_by(ApplicationStageHistory.entered_at.asc())
        ).all()

        stage_history_items = [
            StageHistoryItemResponse(
                id=h.id,
                workflow_stage_id=h.workflow_stage_id,
                stage_name=h.workflow_stage.stage_name if h.workflow_stage else "Unknown",
                stage_code=h.workflow_stage.stage_code if h.workflow_stage else "UNKNOWN",
                status=h.status,
                action_name=h.action_name,
                remarks=h.remarks,
                acted_by_user_id=h.acted_by_user_id,
                acted_by_name=h.acted_by_user.full_name if h.acted_by_user else None,
                entered_at=h.entered_at,
                exited_at=h.exited_at,
            )
            for h in histories
        ]

        # Compute available actions based on current stage and user's role
        user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
        app_status_str = app.status.value if hasattr(app.status, "value") else str(app.status)
        available_actions: List[AvailableActionResponse] = []

        if app_status_str not in [ApplicationStatus.DRAFT.value, ApplicationStatus.CLOSED.value]:
            if app.workflow_definition_id and app.current_stage_id:
                candidate_transitions = db.scalars(
                    select(WorkflowTransition)
                    .options(joinedload(WorkflowTransition.to_stage))
                    .where(
                        WorkflowTransition.workflow_definition_id == app.workflow_definition_id,
                        WorkflowTransition.from_stage_id == app.current_stage_id,
                        WorkflowTransition.is_active.is_(True),
                    )
                ).all()

                for t in candidate_transitions:
                    # Role check: is user's role allowed?
                    if user_role_str in t.allowed_roles:
                        # Once decided, only closure is available
                        if (
                            app_status_str in [ApplicationStatus.APPROVED.value, ApplicationStatus.REJECTED.value]
                            and t.action_name != "CLOSE_APPLICATION"
                        ):
                            continue
                        # Extra safeguard: institution user cannot record decision or approve/reject
                        if user.role == UserRole.INSTITUTION_USER and (
                            t.action_name == "RECORD_DECISION"
                            or t.resulting_status in ["APPROVED", "REJECTED"]
                        ):
                            continue
                        available_actions.append(
                            AvailableActionResponse(
                                transition_id=t.id,
                                action_name=t.action_name,
                                requires_remarks=t.requires_remarks,
                                to_stage_id=t.to_stage_id,
                                to_stage_name=t.to_stage.stage_name if t.to_stage else "Next Stage",
                                resulting_status=t.resulting_status,
                            )
                        )

        return ApplicationWorkflowStateResponse(
            application_id=app.id,
            application_number=app.application_number,
            application_type=app.application_type,
            current_status=app_status_str,
            current_stage_id=app.current_stage_id,
            current_stage_name=app.current_stage,
            workflow_definition_id=app.workflow_definition_id,
            workflow_name=app.workflow_definition.name if app.workflow_definition else None,
            stage_history=stage_history_items,
            available_actions=available_actions,
        )

    @staticmethod
    def execute_workflow_action(
        db: Session,
        application_id: uuid.UUID,
        user: User,
        payload: WorkflowActionRequest,
    ) -> ApplicationWorkflowStateResponse:
        """
        Executes a workflow action against an application using row-level locking.
        Validates role permission, current stage validity, mandatory remarks,
        updates stage & status, closes existing history, and logs new history.
        """
        # 1. Acquire row-level lock on application to prevent race conditions
        app = db.scalar(
            select(Application)
            .where(Application.id == application_id)
            .with_for_update()
        )
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' was not found.",
            )

        # 2. Access boundary check
        if user.role == UserRole.INSTITUTION_USER:
            if app.institution_id != user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Application with ID '{application_id}' was not found.",
                )
        elif user.role == UserRole.REVIEWER:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' is not assigned to this reviewer.",
            )

        clean_action = payload.action_name.strip()
        app_status_str = app.status.value if hasattr(app.status, "value") else str(app.status)
        if app_status_str == ApplicationStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Application is still in DRAFT status. It must be submitted before workflow actions can be executed.",
            )

        if app_status_str == ApplicationStatus.CLOSED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Application is already finalized in CLOSED status. No further workflow transitions are allowed.",
            )

        if (
            app_status_str in [ApplicationStatus.APPROVED.value, ApplicationStatus.REJECTED.value]
            and clean_action != "CLOSE_APPLICATION"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Application has already received a regulatory decision ('{app_status_str}'). Only application closure is permitted.",
            )

        if not app.workflow_definition_id or not app.current_stage_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Application has no active workflow stage configured.",
            )

        # 3. Verify requested transition is configured and active
        transition_query = select(WorkflowTransition).options(
            joinedload(WorkflowTransition.to_stage),
            joinedload(WorkflowTransition.from_stage),
        ).where(
            WorkflowTransition.workflow_definition_id == app.workflow_definition_id,
            WorkflowTransition.action_name == clean_action,
            WorkflowTransition.is_active.is_(True),
        )

        transitions_for_action = db.scalars(transition_query).all()
        if not transitions_for_action:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Workflow action '{clean_action}' is not configured in this workflow.",
            )

        # Filter by current stage
        matching_transitions = [
            t for t in transitions_for_action if t.from_stage_id == app.current_stage_id
        ]
        if not matching_transitions:
            # Action exists in workflow but not from current stage -> stage skip or stale action
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Action '{clean_action}' cannot be performed from stage '{app.current_stage}'. The application may have already transitioned.",
            )

        # If target_stage_id is specified, narrow down
        selected_transition = None
        if payload.target_stage_id:
            for t in matching_transitions:
                if t.to_stage_id == payload.target_stage_id:
                    selected_transition = t
                    break
            if not selected_transition:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"No transition for action '{clean_action}' to target stage '{payload.target_stage_id}' exists.",
                )
        else:
            selected_transition = matching_transitions[0]

        # 4. Role Authorization Check
        user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
        if user_role_str not in selected_transition.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role_str}' is not authorized to perform workflow action '{clean_action}'.",
            )

        # Specific regulatory safeguards:
        # Decision recording must require an authorized official role
        if clean_action == "RECORD_DECISION" or selected_transition.resulting_status in ["APPROVED", "REJECTED"]:
            if user.role not in [UserRole.ADMIN, UserRole.AICTE_OFFICIAL]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Final regulatory decisions require an authorized AICTE Official or Administrator.",
                )
            if user.role == UserRole.INSTITUTION_USER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="An institution user cannot approve or reject their own application.",
                )

        # 5. Remarks Validation
        remarks_text = payload.remarks.strip() if payload.remarks else None
        if selected_transition.requires_remarks or clean_action == "RETURN_FOR_CLARIFICATION":
            if not remarks_text:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Action '{clean_action}' requires explanatory remarks.",
                )

        # 6. Apply Transition within Transaction
        # Close open stage history for current stage
        open_history = db.scalar(
            select(ApplicationStageHistory)
            .where(
                ApplicationStageHistory.application_id == app.id,
                ApplicationStageHistory.workflow_stage_id == app.current_stage_id,
                ApplicationStageHistory.exited_at.is_(None),
            )
            .order_by(ApplicationStageHistory.entered_at.desc())
        )
        now_utc = datetime.now(timezone.utc)
        if open_history:
            open_history.exited_at = now_utc

        # Resolve resulting status
        if selected_transition.resulting_status:
            new_status = ApplicationStatus(selected_transition.resulting_status)
        elif clean_action in STATUS_ACTION_MAP:
            new_status = STATUS_ACTION_MAP[clean_action]
        else:
            new_status = app.status

        # Advance application to target stage
        target_stage = selected_transition.to_stage
        app.current_stage_id = target_stage.id
        app.current_stage = target_stage.stage_name
        app.status = new_status
        app.updated_at = now_utc

        # Log new stage history
        new_status_str = (
            new_status.value if hasattr(new_status, "value") else str(new_status)
        )
        new_history = ApplicationStageHistory(
            application_id=app.id,
            workflow_stage_id=target_stage.id,
            status=new_status_str,
            action_name=clean_action,
            remarks=remarks_text,
            acted_by_user_id=user.id,
            entered_at=now_utc,
        )
        db.add(new_history)

        db.commit()
        db.refresh(app)

        return WorkflowService.get_application_workflow_state(db, app.id, user)
