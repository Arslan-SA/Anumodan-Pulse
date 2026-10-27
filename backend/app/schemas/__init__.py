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
from app.schemas.compliance_requirement import (
    ComplianceRequirementCreate,
    ComplianceRequirementResponse,
    ComplianceRequirementStatusUpdate,
    ComplianceRequirementUpdate,
)
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentExpiringResponse,
    DocumentResponse,
)
from app.schemas.compliance import (
    ComplianceHistoryResponse,
    ComplianceRecordCreate,
    ComplianceRecordDetailResponse,
    ComplianceRecordResponse,
    ComplianceRecordUpdate,
    ComplianceRejectRequest,
    ComplianceVerifyRequest,
)
from app.schemas.notification import (
    NotificationMarkReadResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
)
from app.schemas.reminder_rule import (
    ReminderRuleCreate,
    ReminderRuleResponse,
    ReminderRuleStatusUpdate,
    ReminderRuleUpdate,
)
from app.schemas.escalation import EscalationHistoryResponse

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
    "ComplianceRequirementCreate",
    "ComplianceRequirementUpdate",
    "ComplianceRequirementStatusUpdate",
    "ComplianceRequirementResponse",
    "DocumentResponse",
    "DocumentDetailResponse",
    "DocumentExpiringResponse",
    "ComplianceRecordCreate",
    "ComplianceRecordUpdate",
    "ComplianceVerifyRequest",
    "ComplianceRejectRequest",
    "ComplianceHistoryResponse",
    "ComplianceRecordResponse",
    "ComplianceRecordDetailResponse",
    "NotificationResponse",
    "NotificationUnreadCountResponse",
    "NotificationMarkReadResponse",
    "ReminderRuleCreate",
    "ReminderRuleUpdate",
    "ReminderRuleStatusUpdate",
    "ReminderRuleResponse",
    "EscalationHistoryResponse",
]


