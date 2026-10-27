"""
AICTE FlowOps — Service Layer Registry
"""

from app.services.institution_service import InstitutionService
from app.services.application_service import ApplicationService

__all__ = [
    "InstitutionService",
    "ApplicationService",
]
