"""
AICTE FlowOps — Notification Schemas

Request and response models for user notifications and alert management.
"""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationPriority, NotificationStatus, NotificationType


class NotificationResponse(BaseModel):
    """Sanitized representation of a user notification."""
    id: uuid.UUID
    recipient_user_id: uuid.UUID
    notification_type: NotificationType
    title: str
    message: str
    related_application_id: Optional[uuid.UUID] = None
    related_compliance_id: Optional[uuid.UUID] = None
    related_document_id: Optional[uuid.UUID] = None
    priority: NotificationPriority
    status: NotificationStatus
    created_at: datetime
    read_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationUnreadCountResponse(BaseModel):
    """Unread notifications tally for badges and app shell counters."""
    unread_count: int = Field(..., ge=0, description="Total active unread notifications count")


class NotificationMarkReadResponse(BaseModel):
    """Confirmation payload after bulk or single read status updates."""
    success: bool
    updated_count: int
