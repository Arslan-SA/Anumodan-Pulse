"""
AICTE FlowOps — ORM Models Registry

Exports all domain models for application use and Alembic migration metadata collection.
"""

from app.database import Base
from app.models.enums import ApplicationStatus, ComplianceStatus, UserRole
from app.models.institution import Institution
from app.models.user import User
from app.models.application import Application
from app.models.workflow_stage import WorkflowStage
from app.models.stage_history import ApplicationStageHistory
from app.models.compliance import ComplianceRecord
from app.models.document import Document
from app.models.workflow_definition import WorkflowDefinition
from app.models.workflow_transition import WorkflowTransition
from app.models.compliance_requirement import ComplianceRequirement
from app.models.compliance_history import ComplianceHistory

__all__ = [
    "Base",
    "UserRole",
    "ApplicationStatus",
    "ComplianceStatus",
    "Institution",
    "User",
    "Application",
    "WorkflowStage",
    "ApplicationStageHistory",
    "ComplianceRecord",
    "Document",
    "WorkflowDefinition",
    "WorkflowTransition",
    "ComplianceRequirement",
    "ComplianceHistory",
]

