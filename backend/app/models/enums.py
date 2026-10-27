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


class NotificationType(str, Enum):
    """Categorized notification trigger events."""
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED"
    APPLICATION_RETURNED = "APPLICATION_RETURNED"
    APPLICATION_STAGE_UPDATED = "APPLICATION_STAGE_UPDATED"
    EVC_SCHEDULED = "EVC_SCHEDULED"
    COMPLIANCE_DUE_SOON = "COMPLIANCE_DUE_SOON"
    COMPLIANCE_OVERDUE = "COMPLIANCE_OVERDUE"
    COMPLIANCE_SUBMITTED = "COMPLIANCE_SUBMITTED"
    COMPLIANCE_VERIFIED = "COMPLIANCE_VERIFIED"
    COMPLIANCE_REJECTED = "COMPLIANCE_REJECTED"
    DOCUMENT_EXPIRING = "DOCUMENT_EXPIRING"
    DOCUMENT_EXPIRED = "DOCUMENT_EXPIRED"
    ESCALATION = "ESCALATION"


class NotificationPriority(str, Enum):
    """Notification urgency levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NotificationStatus(str, Enum):
    """Read/archive status of user notifications."""
    UNREAD = "UNREAD"
    READ = "READ"
    ARCHIVED = "ARCHIVED"

