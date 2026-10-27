"""
AICTE FlowOps — Service Layer Registry
"""

from app.services.institution_service import InstitutionService
from app.services.application_service import ApplicationService
from app.services.workflow_service import WorkflowService
from app.services.compliance_service import ComplianceService
from app.services.document_service import DocumentService
from app.services.notification_service import NotificationService
from app.services.deadline_service import DeadlineService
from app.services.dashboard_service import DashboardService
from app.services.report_service import ReportService
from app.services.ai_provider import BaseAIProvider, DeterministicFallbackProvider, MockAIProvider, get_ai_provider
from app.services.ai_service import AIService

__all__ = [
    "InstitutionService",
    "ApplicationService",
    "WorkflowService",
    "ComplianceService",
    "DocumentService",
    "NotificationService",
    "DeadlineService",
    "DashboardService",
    "ReportService",
    "AIService",
    "BaseAIProvider",
    "DeterministicFallbackProvider",
    "MockAIProvider",
    "get_ai_provider",
]


