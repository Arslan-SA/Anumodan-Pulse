"""
AICTE FlowOps — Institution Schemas

Request and response models for technical institutions.
"""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InstitutionBase(BaseModel):
    institution_name: str = Field(..., min_length=2, max_length=255)
    institution_type: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)


class InstitutionUpdate(BaseModel):
    """
    Permitted fields that an institution user may update.
    Does NOT allow updating institution_id or institution_code.
    """
    institution_name: Optional[str] = Field(None, min_length=2, max_length=255)
    institution_type: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)


class InstitutionResponse(InstitutionBase):
    """Safe public representation of a technical institution."""
    id: uuid.UUID
    institution_code: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
