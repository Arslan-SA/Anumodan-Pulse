"""
AICTE FlowOps — User Management Endpoints (ADMIN Only)

Handles:
- GET   /api/v1/users              (List users with pagination & role filtering)
- GET   /api/v1/users/{user_id}    (Retrieve single user profile)
- PATCH /api/v1/users/{user_id}/status (Activate / deactivate user account)
- PATCH /api/v1/users/{user_id}/role   (Update user role)
"""

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserResponse, UserRoleUpdate, UserStatusUpdate

router = APIRouter()


@router.get(
    "",
    response_model=List[UserResponse],
    summary="List Users (Admin)",
    description="Paginated user directory with optional filtering by role. Accessible to ADMIN only.",
)
def list_users(
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    role: Optional[UserRole] = Query(None, description="Filter by platform role"),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    return db.scalars(query).all()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get User By ID (Admin)",
    description="Retrieve a user profile. Accessible to ADMIN only.",
)
def get_user_by_id(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' was not found.",
        )
    return user


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="Update User Status (Admin)",
    description="Activate or deactivate a user account. Prevents locking out the last active administrator.",
)
def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' was not found.",
        )

    # Protect against locking out the only active administrator
    if target_user.role == UserRole.ADMIN and not payload.is_active:
        active_admin_count = db.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.ADMIN,
                User.is_active == True,  # noqa: E712
            )
        )
        if active_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the platform's last active administrator.",
            )

    target_user.is_active = payload.is_active
    db.commit()
    db.refresh(target_user)
    return target_user


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Update User Role (Admin)",
    description="Change a user's role. Prevents self-role tampering and demoting the last active administrator.",
)
def update_user_role(
    user_id: uuid.UUID,
    payload: UserRoleUpdate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' was not found.",
        )

    # Prevent self-role modification to eliminate accidental lockout or elevation loopholes
    if target_user.id == current_admin.id and payload.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot demote their own account role.",
        )

    # Protect against demoting the last active administrator
    if target_user.role == UserRole.ADMIN and payload.role != UserRole.ADMIN:
        active_admin_count = db.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.ADMIN,
                User.is_active == True,  # noqa: E712
            )
        )
        if active_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the platform's last active administrator.",
            )

    target_user.role = payload.role
    db.commit()
    db.refresh(target_user)
    return target_user
