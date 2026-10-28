"""
AICTE FlowOps — OTP Verification & Google Authentication Test Suite

Tests:
- OTP generation, dispatch, expiration, and attempt rate-limiting.
- Registration with Email OTP verification and institution affiliation.
- Passwordless login via Email OTP.
- Google Authentication token verification, user auto-provisioning, and login.
- Public institution lookup for user registration.
"""

from datetime import datetime, timedelta, timezone
import io
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.email_otp import EmailOTP
from app.models.enums import UserRole
from app.models.institution import Institution
from app.models.user import User
from app.services.google_auth_service import GoogleAuthService
from app.services.otp_service import OTPService
from app.utils.security import hash_password


@pytest.fixture
def institution_fixture():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Vidyapeeth College {suffix}",
            institution_code=f"VID-{suffix}",
            institution_type="Engineering",
            state="Maharashtra",
            district="Pune",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def active_user(institution_fixture):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Prof. Verma {suffix}",
            email=f"verma_{suffix}@vidyapeeth.edu",
            hashed_password=hash_password("Aicte@Password2026"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_fixture.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


# ── OTP Service & Endpoints Tests ────────────────────────────────────────────

def test_send_and_verify_otp(client: TestClient):
    """Test generating, sending, and verifying a 6-digit OTP code."""
    email = f"test_{uuid.uuid4().hex[:6]}@example.com"

    # 1. Send OTP
    send_res = client.post(
        "/api/v1/auth/otp/send",
        json={"email": email, "purpose": "register"},
    )
    assert send_res.status_code == 200
    data = send_res.json()
    assert "dev_otp" in data
    code = data["dev_otp"]
    assert len(code) == 6
    assert code.isdigit()

    # 2. Verify with wrong OTP
    bad_res = client.post(
        "/api/v1/auth/otp/verify",
        json={"email": email, "otp_code": "000000", "purpose": "register"},
    )
    assert bad_res.status_code == 400

    # 3. Verify with correct OTP
    good_res = client.post(
        "/api/v1/auth/otp/verify",
        json={"email": email, "otp_code": code, "purpose": "register"},
    )
    assert good_res.status_code == 200
    assert good_res.json()["verified"] is True


def test_otp_attempt_limits(client: TestClient):
    """Exceeding 5 incorrect attempts locks out the OTP."""
    email = f"limit_{uuid.uuid4().hex[:6]}@example.com"
    send_res = client.post(
        "/api/v1/auth/otp/send",
        json={"email": email, "purpose": "register"},
    )
    code = send_res.json()["dev_otp"]

    # Enter wrong code 6 times
    for _ in range(6):
        client.post(
            "/api/v1/auth/otp/verify",
            json={"email": email, "otp_code": "999999", "purpose": "register"},
        )

    # Even correct code is now rejected because max attempts exceeded
    locked_res = client.post(
        "/api/v1/auth/otp/verify",
        json={"email": email, "otp_code": code, "purpose": "register"},
    )
    assert locked_res.status_code == 400


def test_otp_login_flow(client: TestClient, active_user: User):
    """Passwordless login using an email OTP."""
    # 1. Request OTP for login
    send_res = client.post(
        "/api/v1/auth/otp/send",
        json={"email": active_user.email, "purpose": "login"},
    )
    assert send_res.status_code == 200
    otp_code = send_res.json()["dev_otp"]

    # 2. Login with OTP
    login_res = client.post(
        "/api/v1/auth/otp/login",
        json={"email": active_user.email, "otp_code": otp_code},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["user"]["email"] == active_user.email

    # 3. Verify accessing /me with this token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == active_user.email


def test_otp_login_nonexistent_user_rejected(client: TestClient):
    """Requesting login OTP for an unregistered email returns 404."""
    res = client.post(
        "/api/v1/auth/otp/send",
        json={"email": "nobody_registered_here@example.com", "purpose": "login"},
    )
    assert res.status_code == 404


# ── Registration with OTP Tests ──────────────────────────────────────────────

def test_register_institution_user_with_otp(client: TestClient, institution_fixture: Institution):
    """Register institution representative using email OTP and existing institution ID."""
    reg_email = f"dean_{uuid.uuid4().hex[:6]}@vidyapeeth.edu"

    # Send OTP
    send_res = client.post(
        "/api/v1/auth/otp/send",
        json={"email": reg_email, "purpose": "register"},
    )
    otp_code = send_res.json()["dev_otp"]

    # Complete registration
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Dean Dr. R. K. Joshi",
            "email": reg_email,
            "password": "SecurePassword@2026",
            "institution_id": str(institution_fixture.id),
            "otp_code": otp_code,
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["email"] == reg_email
    assert reg_data["role"] == "INSTITUTION_USER"


def test_register_with_new_institution_details(client: TestClient):
    """Register with institution name and code if not selecting an existing ID."""
    suffix = uuid.uuid4().hex[:6]
    reg_email = f"registrar_{suffix}@newcampus.ac.in"

    # Send OTP
    send_res = client.post(
        "/api/v1/auth/otp/send",
        json={"email": reg_email, "purpose": "register"},
    )
    otp_code = send_res.json()["dev_otp"]

    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": f"Registrar New Campus {suffix}",
            "email": reg_email,
            "password": "Aicte@SecureCampus2026",
            "institution_name": f"New Institute of Technology {suffix}",
            "institution_code": f"NIT-{suffix.upper()}",
            "otp_code": otp_code,
        },
    )
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert data["email"] == reg_email
    assert data["role"] == "INSTITUTION_USER"
    assert "access_token" in data


def test_register_duplicate_email_conflict(client: TestClient, active_user: User):
    """Attempting to register with an already existing email returns 409 Conflict."""
    res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Duplicate User",
            "email": active_user.email,
            "password": "Aicte@Secure2026",
            "institution_id": str(active_user.institution_id),
        },
    )
    assert res.status_code == 409


# ── Google Authentication Tests ──────────────────────────────────────────────

def test_google_auth_new_user_provisioning(client: TestClient, institution_fixture: Institution):
    """Signing in with Google auto-provisions a new Institution User account."""
    suffix = uuid.uuid4().hex[:6]
    mock_email = f"google.user.{suffix}@gmail.com"
    mock_token = f"demo_google_token:{mock_email}:Dr. Sunita Patel"

    res = client.post(
        "/api/v1/auth/google",
        json={
            "credential": mock_token,
            "institution_id": str(institution_fixture.id),
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == mock_email
    assert data["user"]["role"] == "INSTITUTION_USER"


def test_google_auth_existing_user(client: TestClient, active_user: User):
    """Signing in with Google for an existing registered email logs in smoothly."""
    mock_token = f"demo_google_token:{active_user.email}:{active_user.full_name}"

    res = client.post(
        "/api/v1/auth/google",
        json={"credential": mock_token},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == active_user.email


# ── Institutions Public Lookup Test ──────────────────────────────────────────

def test_institutions_lookup_endpoint(client: TestClient, institution_fixture: Institution):
    """Public lookup returns institutions matching query."""
    res = client.get(f"/api/v1/auth/institutions/lookup?q={institution_fixture.institution_code}")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert any(i["institution_code"] == institution_fixture.institution_code for i in items)
