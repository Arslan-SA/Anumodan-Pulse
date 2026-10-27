"""
AICTE FlowOps — Core Domain Enums

Enumerations for user roles, application lifecycle statuses,
and compliance tracking.
"""

from enum import Enum


class UserRole(str, Enum):
    """Platform user roles."""
    ADMIN = "ADMIN"
    AICTE_OFFICIAL = "AICTE_OFFICIAL"
    INSTITUTION_USER = "INSTITUTION_USER"
    REVIEWER = "REVIEWER"


class ApplicationStatus(str, Enum):
    """Application processing lifecycle statuses."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_SCRUTINY = "UNDER_SCRUTINY"
    RETURNED_FOR_CLARIFICATION = "RETURNED_FOR_CLARIFICATION"
    EVC_PENDING = "EVC_PENDING"
    EVC_SCHEDULED = "EVC_SCHEDULED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class ComplianceStatus(str, Enum):
    """Compliance undertaking and document verification statuses."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    UNDER_VERIFICATION = "UNDER_VERIFICATION"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    OVERDUE = "OVERDUE"
