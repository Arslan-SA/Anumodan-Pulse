"""
AICTE FlowOps — ReminderRule Schemas

Request and response models for configurable deadline reminder and alert rules.
"""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationPriority


class ReminderRuleCreate(BaseModel):
    """Admin payload to register a new configurable reminder schedule."""
    name: str = Field(..., min_length=2, max_length=255, description="Rule display label")
    event_type: str = Field(..., min_length=2, max_length=50, description="Target trigger event type")
    days_before_deadline: Optional[int] = Field(None, ge=1, le=365, description="Pre-deadline warning window (days)")
    overdue_days: Optional[int] = Field(None, ge=1, le=365, description="Post-deadline overdue window (days)")
    target_role: Optional[str] = Field(None, max_length=50, description="Target recipient role filter")
    priority: NotificationPriority = Field(NotificationPriority.MEDIUM, description="Notification urgency")
    is_active: bool = Field(True, description="Whether rule is evaluated in background checks")


class ReminderRuleUpdate(BaseModel):
    """Admin payload to modify reminder rule parameters."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    event_type: Optional[str] = Field(None, min_length=2, max_length=50)
    days_before_deadline: Optional[int] = Field(None, ge=1, le=365)
    overdue_days: Optional[int] = Field(None, ge=1, le=365)
    target_role: Optional[str] = Field(None, max_length=50)
    priority: Optional[NotificationPriority] = None
    is_active: Optional[bool] = None


class ReminderRuleStatusUpdate(BaseModel):
    """Admin payload to toggle active evaluation status."""
    is_active: bool


class ReminderRuleResponse(BaseModel):
    """Public representation of a configured reminder rule."""
    id: uuid.UUID
    name: str
    event_type: str
    days_before_deadline: Optional[int] = None
    overdue_days: Optional[int] = None
    target_role: Optional[str] = None
    priority: NotificationPriority
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
