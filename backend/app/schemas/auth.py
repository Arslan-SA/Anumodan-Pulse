"""
AICTE FlowOps — Authentication Schemas

Pydantic models for registration, login, token exchange, OTP verification,
and Google authentication.
"""

from typing import List, Optional
import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserResponse
from app.utils.security import validate_password_strength


class RegisterRequest(BaseModel):
    """
    Public registration request for institution users.
    Allows registering INSTITUTION_USER accounts either by linking an existing
    institution ID or supplying institution details, verified with an optional OTP.
    """
    full_name: str = Field(..., min_length=2, max_length=255, description="Official full name")
    email: EmailStr = Field(..., description="Institutional email address")
    password: str = Field(..., min_length=8, description="Strong password compliant with policy")
    institution_id: Optional[uuid.UUID] = Field(None, description="Optional ID of existing technical institution")
    institution_name: Optional[str] = Field(None, min_length=3, max_length=255, description="Name for new institution if not selected")
    institution_code: Optional[str] = Field(None, min_length=2, max_length=50, description="Code for new institution if not selected")
    otp_code: Optional[str] = Field(None, min_length=6, max_length=6, description="6-digit verification code received by email")

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class RegisterResponse(UserResponse):
    """Registration response returning user profile and access token for auto-login."""
    access_token: Optional[str] = None
    token_type: Optional[str] = "bearer"


class LoginRequest(BaseModel):
    """Credentials payload for JWT access token acquisition."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")


class TokenResponse(BaseModel):
    """Standard Bearer token response."""
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


class SendOtpRequest(BaseModel):
    """Request payload to trigger sending a 6-digit verification code."""
    email: EmailStr = Field(..., description="Email address to receive the verification OTP")
    purpose: str = Field("register", pattern="^(register|login)$", description="Intended purpose: 'register' or 'login'")


class SendOtpResponse(BaseModel):
    """Response payload confirming OTP dispatch."""
    message: str
    expires_in_minutes: int
    dev_otp: Optional[str] = None


class VerifyOtpRequest(BaseModel):
    """Request payload to verify a 6-digit OTP code."""
    email: EmailStr = Field(..., description="Email address associated with the OTP")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit numeric verification code")
    purpose: str = Field("register", pattern="^(register|login)$", description="Purpose: 'register' or 'login'")


class VerifyOtpResponse(BaseModel):
    """Response payload confirming OTP verification status."""
    verified: bool
    message: str


class OtpLoginRequest(BaseModel):
    """Request payload to authenticate and acquire a JWT session using an email OTP."""
    email: EmailStr = Field(..., description="Registered email address")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit numeric verification code")


class GoogleAuthRequest(BaseModel):
    """Payload for Google Identity Services token exchange."""
    credential: str = Field(..., min_length=1, description="Google OAuth ID Token or demo credential")
    institution_id: Optional[uuid.UUID] = Field(None, description="Optional institution ID to affiliate with")


class InstitutionLookupItem(BaseModel):
    """Public institution summary for the registration selector."""
    id: uuid.UUID
    institution_name: str
    institution_code: str
    state: Optional[str] = None
    district: Optional[str] = None
