"""
AICTE FlowOps — API Dependencies & Role-Based Access Control (RBAC)

Provides:
- OAuth2 password bearer token extractor
- Current user authentication and token validation
- Account active-status verification
- Role-based authorization dependencies (ADMIN, AICTE_OFFICIAL, INSTITUTION_USER, REVIEWER)
"""

from typing import Callable, List, Optional
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.utils.security import decode_access_token

# OAuth2 scheme configured with the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate the incoming JWT Bearer token and retrieve the user from the database.
    Raises HTTP 401 Unauthorized for expired, invalid, or missing credentials.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token has expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        sub: Optional[str] = payload.get("sub")
        if not sub:
            raise credentials_exception
        user_id = uuid.UUID(sub)
    except jwt.ExpiredSignatureError:
        raise expired_exception
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensure the authenticated user account is active.
    Raises HTTP 403 Forbidden if deactivated.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact an administrator.",
        )
    return current_user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """
    Dependency factory to enforce role-based access control (RBAC).
    Returns 403 Forbidden if the active user does not have one of the required roles.
    """
    def role_dependency(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        user_role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        allowed_vals = [r.value if hasattr(r, "value") else str(r) for r in allowed_roles]
        if user_role_val not in allowed_vals:
            role_names = ", ".join(allowed_vals)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of the following roles: {role_names}",
            )
        return current_user

    return role_dependency


# Reusable role-specific dependencies
require_admin = require_roles(UserRole.ADMIN)
require_aicte_official = require_roles(UserRole.AICTE_OFFICIAL)
require_institution_user = require_roles(UserRole.INSTITUTION_USER)
require_reviewer = require_roles(UserRole.REVIEWER)
require_official_or_admin = require_roles(UserRole.ADMIN, UserRole.AICTE_OFFICIAL)

