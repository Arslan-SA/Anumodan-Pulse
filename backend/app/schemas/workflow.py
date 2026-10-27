"""
AICTE FlowOps — Workflow Pydantic Schemas

Defines request/response schemas for workflow definitions, stages,
transitions, actions, and application workflow state.
"""

from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


# ── Workflow Stage Schemas ───────────────────────────────────────────
class WorkflowStageBase(BaseModel):
    stage_name: str = Field(..., min_length=2, max_length=100)
    stage_code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    sequence_order: int = Field(0, ge=0)
    is_active: bool = True


class WorkflowStageCreate(WorkflowStageBase):
    pass


class WorkflowStageResponse(WorkflowStageBase):
    id: uuid.UUID
    workflow_definition_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Workflow Transition Schemas ──────────────────────────────────────
class WorkflowTransitionBase(BaseModel):
    action_name: str = Field(..., min_length=2, max_length=100)
    allowed_roles: List[str] = Field(default_factory=list)
    requires_remarks: bool = False
    resulting_status: Optional[str] = Field(None, max_length=50)
    is_active: bool = True


class WorkflowTransitionCreate(WorkflowTransitionBase):
    from_stage_id: Optional[uuid.UUID] = None
    to_stage_id: uuid.UUID


class WorkflowTransitionUpdate(BaseModel):
    action_name: Optional[str] = Field(None, min_length=2, max_length=100)
    allowed_roles: Optional[List[str]] = None
    requires_remarks: Optional[bool] = None
    resulting_status: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    from_stage_id: Optional[uuid.UUID] = None
    to_stage_id: Optional[uuid.UUID] = None


class WorkflowTransitionResponse(WorkflowTransitionBase):
    id: uuid.UUID
    workflow_definition_id: uuid.UUID
    from_stage_id: Optional[uuid.UUID] = None
    to_stage_id: uuid.UUID
    from_stage_name: Optional[str] = None
    to_stage_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Workflow Definition Schemas ──────────────────────────────────────
class WorkflowDefinitionBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    application_type: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = True


class WorkflowDefinitionCreate(WorkflowDefinitionBase):
    pass


class WorkflowDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    application_type: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class WorkflowDefinitionResponse(WorkflowDefinitionBase):
    id: uuid.UUID
    stages_count: int = 0
    transitions_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowDefinitionDetailResponse(WorkflowDefinitionBase):
    id: uuid.UUID
    stages: List[WorkflowStageResponse] = Field(default_factory=list)
    transitions: List[WorkflowTransitionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Application Workflow State & Action Schemas ─────────────────────
class AvailableActionResponse(BaseModel):
    transition_id: uuid.UUID
    action_name: str
    requires_remarks: bool
    to_stage_id: uuid.UUID
    to_stage_name: str
    resulting_status: Optional[str] = None


class StageHistoryItemResponse(BaseModel):
    id: uuid.UUID
    workflow_stage_id: uuid.UUID
    stage_name: str
    stage_code: str
    status: str
    action_name: Optional[str] = None
    remarks: Optional[str] = None
    acted_by_user_id: Optional[uuid.UUID] = None
    acted_by_name: Optional[str] = None
    entered_at: datetime
    exited_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationWorkflowStateResponse(BaseModel):
    application_id: uuid.UUID
    application_number: str
    application_type: str
    current_status: str
    current_stage_id: Optional[uuid.UUID] = None
    current_stage_name: Optional[str] = None
    workflow_definition_id: Optional[uuid.UUID] = None
    workflow_name: Optional[str] = None
    stage_history: List[StageHistoryItemResponse] = Field(default_factory=list)
    available_actions: List[AvailableActionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class WorkflowActionRequest(BaseModel):
    action_name: str = Field(..., min_length=2, max_length=100)
    remarks: Optional[str] = Field(None, max_length=2000)
    target_stage_id: Optional[uuid.UUID] = None
