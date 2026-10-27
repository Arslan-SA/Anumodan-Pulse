"""
AICTE FlowOps — Schemas Registry
"""

from app.schemas.common import PaginatedResponse
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse, UserRoleUpdate, UserStatusUpdate
from app.schemas.institution import InstitutionBase, InstitutionResponse, InstitutionUpdate
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetailResponse,
    ApplicationResponse,
    ApplicationUpdate,
)

__all__ = [
    "PaginatedResponse",
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "UserResponse",
    "UserStatusUpdate",
    "UserRoleUpdate",
    "InstitutionBase",
    "InstitutionResponse",
    "InstitutionUpdate",
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationResponse",
    "ApplicationDetailResponse",
]
