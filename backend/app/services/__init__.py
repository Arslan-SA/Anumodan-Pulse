"""
AICTE FlowOps — Service Layer Registry
"""

from app.services.institution_service import InstitutionService
from app.services.application_service import ApplicationService
from app.services.workflow_service import WorkflowService
from app.services.compliance_service import ComplianceService
from app.services.document_service import DocumentService

__all__ = [
    "InstitutionService",
    "ApplicationService",
    "WorkflowService",
    "ComplianceService",
    "DocumentService",
]

