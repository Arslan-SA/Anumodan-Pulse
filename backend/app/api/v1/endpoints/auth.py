"""
AICTE FlowOps — Authentication Endpoints

Handles:
- POST /api/v1/auth/register            (Institution user self-registration with OTP verification)
- POST /api/v1/auth/login               (JWT Bearer password authentication)
- POST /api/v1/auth/otp/send            (Dispatch 6-digit email verification code)
- POST /api/v1/auth/otp/verify          (Verify 6-digit email OTP)
- POST /api/v1/auth/otp/login           (Passwordless login via email OTP)
- POST /api/v1/auth/google              (Google Identity Services / OAuth login & auto-provisioning)
- GET  /api/v1/auth/institutions/lookup (Public institution directory for registration picker)
- GET  /api/v1/auth/me                  (Current active user profile)
- POST /api/v1/auth/logout              (Stateless session clearance)
"""

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.enums import UserRole
from app.models.institution import Institution
from app.models.user import User
from app.schemas.auth import (
    GoogleAuthRequest,
    InstitutionLookupItem,
    LoginRequest,
    OtpLoginRequest,
    RegisterRequest,
    RegisterResponse,
    SendOtpRequest,
    SendOtpResponse,
    TokenResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.schemas.user import UserResponse
from app.services.google_auth_service import GoogleAuthService
from app.services.otp_service import OTPService
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter()


def _issue_token_response(user: User) -> TokenResponse:
    """Helper to generate JWT bearer token for an active user."""
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
    "/institutions/lookup",
    response_model=List[InstitutionLookupItem],
    summary="List Institutions for Registration",
    description="Public list of technical institutions for user onboarding selector.",
)
def lookup_institutions(
    q: Optional[str] = Query(None, description="Search query for institution name or code"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = select(Institution).order_by(Institution.institution_name.asc())
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.where(
            (Institution.institution_name.ilike(term)) | (Institution.institution_code.ilike(term))
        )
    institutions = db.scalars(query.limit(limit)).all()
    return [
        InstitutionLookupItem(
            id=inst.id,
            institution_name=inst.institution_name,
            institution_code=inst.institution_code,
            state=inst.state,
            district=inst.district,
        )
        for inst in institutions
    ]


@router.post(
    "/otp/send",
    response_model=SendOtpResponse,
    summary="Send Email Verification Code",
    description="Generates a 6-digit OTP and delivers it to the requested email for registration or login.",
)
def send_otp(
    payload: SendOtpRequest,
    db: Session = Depends(get_db),
):
    # If purpose is 'login', verify user exists and is active
    if payload.purpose == "login":
        user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account registered with this email address.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is deactivated. Contact an AICTE administrator.",
            )

    result = OTPService.send_otp(db, str(payload.email), purpose=payload.purpose)
    return SendOtpResponse(**result)


@router.post(
    "/otp/verify",
    response_model=VerifyOtpResponse,
    summary="Verify Email OTP",
    description="Validates a 6-digit passcode without immediately consuming it for multi-step flows.",
)
def verify_otp(
    payload: VerifyOtpRequest,
    db: Session = Depends(get_db),
):
    is_valid = OTPService.verify_otp(
        db,
        str(payload.email),
        payload.otp_code,
        purpose=payload.purpose,
        consume=False,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code. Please check your code or request a new one.",
        )
    return VerifyOtpResponse(verified=True, message="Verification code confirmed successfully.")


@router.post(
    "/otp/login",
    response_model=TokenResponse,
    summary="Passwordless Login via Email OTP",
    description="Authenticates an active user using a verified 6-digit one-time passcode.",
)
def login_with_otp(
    payload: OtpLoginRequest,
    db: Session = Depends(get_db),
):
    # Verify and consume OTP
    is_valid = OTPService.verify_otp(
        db,
        str(payload.email),
        payload.otp_code,
        purpose="login",
        consume=True,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired verification code. Please try again.",
        )

    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact an AICTE administrator.",
        )

    return _issue_token_response(user)


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Sign in with Google",
    description="Verifies a Google OAuth ID Token or demo credential and signs in / auto-provisions the user.",
)
def login_with_google(
    payload: GoogleAuthRequest,
    db: Session = Depends(get_db),
):
    google_data = GoogleAuthService.verify_google_id_token(payload.credential)
    user = GoogleAuthService.authenticate_or_register_user(
        db,
        google_data,
        institution_id=payload.institution_id,
    )
    return _issue_token_response(user)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Institution User",
    description="Public registration for institution officials. Verifies OTP if supplied and auto-logs in.",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    # 1. Verify OTP code if supplied
    if payload.otp_code:
        is_valid = OTPService.verify_otp(
            db,
            str(payload.email),
            payload.otp_code,
            purpose="register",
            consume=True,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code. Please request a new one.",
            )

    # 2. Check for duplicate email
    normalized_email = payload.email.lower().strip()
    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please sign in instead.",
        )

    # 3. Associate or create institution
    institution: Optional[Institution] = None
    if payload.institution_id:
        institution = db.get(Institution, payload.institution_id)
        if not institution:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Institution with ID '{payload.institution_id}' was not found.",
            )
    elif payload.institution_name and payload.institution_code:
        # Check if code already taken
        code_check = db.scalar(
            select(Institution).where(Institution.institution_code == payload.institution_code.strip())
        )
        if code_check:
            institution = code_check
        else:
            institution = Institution(
                institution_name=payload.institution_name.strip(),
                institution_code=payload.institution_code.strip().upper(),
                institution_type="Engineering & Technology",
                state="Delhi",
                district="New Delhi",
                email=normalized_email,
            )
            db.add(institution)
            db.flush()
    else:
        # Fallback to first existing institution
        institution = db.scalar(select(Institution).order_by(Institution.created_at.asc()))

    if not institution:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please select or provide an institution to affiliate your account with.",
        )

    # 4. Create user with strictly restricted INSTITUTION_USER role
    new_user = User(
        full_name=payload.full_name.strip(),
        email=normalized_email,
        hashed_password=hash_password(payload.password),
        role=UserRole.INSTITUTION_USER,
        institution_id=institution.id,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token_claims = {
        "sub": str(new_user.id),
        "email": new_user.email,
        "role": new_user.role.value if hasattr(new_user.role, "value") else str(new_user.role),
        "full_name": new_user.full_name,
    }
    access_token = create_access_token(data=token_claims)

    return RegisterResponse(
        id=new_user.id,
        full_name=new_user.full_name,
        email=new_user.email,
        role=new_user.role,
        is_active=new_user.is_active,
        institution_id=new_user.institution_id,
        created_at=new_user.created_at,
        access_token=access_token,
        token_type="bearer",
    )


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
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        email = body.get("email", "").lower().strip()
        password = body.get("password", "")
    else:
        form = await request.form()
        email = str(form.get("username", "")).lower().strip()
        password = str(form.get("password", ""))

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.scalar(select(User).where(User.email == email))

    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Please contact an AICTE administrator.",
        )

    return _issue_token_response(user)


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
