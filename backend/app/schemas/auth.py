"""
AICTE FlowOps — Authentication Schemas

Pydantic models for registration, login, and token exchange.
"""

from typing import Optional
import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserResponse
from app.utils.security import validate_password_strength


class RegisterRequest(BaseModel):
    """
    Public registration request for institution users.
    Only allows registering INSTITUTION_USER accounts with a valid institution_id.
    """
    full_name: str = Field(..., min_length=2, max_length=255, description="Official full name")
    email: EmailStr = Field(..., description="Institutional email address")
    password: str = Field(..., min_length=8, description="Strong password compliant with policy")
    institution_id: uuid.UUID = Field(..., description="ID of the registered technical institution")

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class LoginRequest(BaseModel):
    """Credentials payload for JWT access token acquisition."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")


class TokenResponse(BaseModel):
    """Standard Bearer token response."""
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None
