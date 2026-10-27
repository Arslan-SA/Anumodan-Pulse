"""
AICTE FlowOps — Authentication Endpoints

Handles:
- POST /api/v1/auth/register (Institution user self-registration)
- POST /api/v1/auth/login    (JWT Bearer authentication)
- GET  /api/v1/auth/me       (Current active user profile)
- POST /api/v1/auth/logout   (Stateless session clearance)
"""

from typing import Union
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.enums import UserRole
from app.models.institution import Institution
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Institution User",
    description="Public registration for institution officials. Always assigns INSTITUTION_USER role.",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    # 1. Verify institution exists
    institution = db.get(Institution, payload.institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Institution with ID '{payload.institution_id}' was not found.",
        )

    # 2. Check for duplicate email
    existing_user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    # 3. Create user with strictly restricted INSTITUTION_USER role
    new_user = User(
        full_name=payload.full_name.strip(),
        email=payload.email.lower().strip(),
        hashed_password=hash_password(payload.password),
        role=UserRole.INSTITUTION_USER,
        institution_id=institution.id,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate & Obtain JWT Token",
    description="Accepts JSON credentials or OAuth2 form data. Returns a signed JWT access token.",
)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    # Support both JSON payload and OAuth2 form-data for Swagger UI compatibility
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        email = body.get("email", "").lower().strip()
        password = body.get("password", "")
    else:
        form = await request.form()
        # OAuth2 form uses 'username' field for email
        email = str(form.get("username", "")).lower().strip()
        password = str(form.get("password", ""))

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query user by normalized email
    user = db.scalar(select(User).where(User.email == email))

    # Constant-time-safe verification: prevent account enumeration
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reject inactive accounts
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Please contact an AICTE administrator.",
        )

    # Generate JWT with subject and role claims
    token_claims = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "full_name": user.full_name,
    }
    access_token = create_access_token(data=token_claims)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User Profile",
    description="Returns the profile and role of the currently authenticated active user.",
)
def get_profile(
    current_user: User = Depends(get_current_active_user),
):
    return current_user


@router.post(
    "/logout",
    summary="Log Out User",
    description="Stateless token logout instruction. The client discards the local bearer token.",
)
def logout(
    current_user: User = Depends(get_current_active_user),
):
    return {
        "message": (
            "Successfully logged out. In this stateless JWT implementation, the client removes "
            "the stored token from storage. Previously issued tokens will expire automatically."
        ),
        "user_id": str(current_user.id),
    }
