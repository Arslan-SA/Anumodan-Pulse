"""
AICTE FlowOps — Schemas Registry
"""

from app.schemas.common import PaginatedResponse
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse, UserRoleUpdate, UserStatusUpdate
from app.schemas.institution import InstitutionBase, InstitutionResponse, InstitutionUpdate
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetailResponse,
    ApplicationResponse,
    ApplicationUpdate,
)
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

__all__ = [
    "PaginatedResponse",
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "UserResponse",
    "UserStatusUpdate",
    "UserRoleUpdate",
    "InstitutionBase",
    "InstitutionResponse",
    "InstitutionUpdate",
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationResponse",
    "ApplicationDetailResponse",
    "WorkflowDefinitionCreate",
    "WorkflowDefinitionUpdate",
    "WorkflowDefinitionResponse",
    "WorkflowDefinitionDetailResponse",
    "WorkflowStageCreate",
    "WorkflowStageResponse",
    "WorkflowTransitionCreate",
    "WorkflowTransitionUpdate",
    "WorkflowTransitionResponse",
    "AvailableActionResponse",
    "StageHistoryItemResponse",
    "ApplicationWorkflowStateResponse",
    "WorkflowActionRequest",
]

