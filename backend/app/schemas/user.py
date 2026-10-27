"""
AICTE FlowOps — User Pydantic Schemas

Defines request/response schemas for user profiles and administrative updates.
"""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr


class UserResponse(UserBase):
    """Safe public representation of a user — never exposes password hashes."""
    id: uuid.UUID
    role: UserRole
    is_active: bool
    institution_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserStatusUpdate(BaseModel):
    """Administrative status change (active/inactive)."""
    is_active: bool


class UserRoleUpdate(BaseModel):
    """Administrative role change."""
    role: UserRole
