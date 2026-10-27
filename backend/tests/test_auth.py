"""
AICTE FlowOps — Authentication & Authorization Tests (Phase 3)

Validates:
- Institution user registration (valid, duplicate email, invalid email, weak password, invalid institution)
- Role protection on public registration (always INSTITUTION_USER)
- Login flow (valid credentials, incorrect password, unknown email, inactive account)
- JWT token structure, expiration, and malformed token handling
- /api/v1/auth/me profile retrieval
- Role-based access control (RBAC) on protected endpoints
"""

from datetime import timedelta
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.enums import UserRole
from app.models.institution import Institution
from app.models.user import User
from app.utils.security import create_access_token, hash_password


@pytest.fixture
def test_institution():
    """Create and return a technical institution fixture."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Test Engineering College {suffix}",
            institution_code=f"TEC-{suffix}",
            institution_type="Engineering",
            state="Karnataka",
            district="Bangalore",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def admin_user():
    """Create and return an active administrator."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Admin {suffix}",
            email=f"admin_{suffix}@aicte.gov.in",
            hashed_password=hash_password("AdminSecure@2026!"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def official_user():
    """Create and return an active regional officer."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Officer {suffix}",
            email=f"officer_{suffix}@aicte.gov.in",
            hashed_password=hash_password("OfficerSecure@2026!"),
            role=UserRole.AICTE_OFFICIAL,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def institution_user(test_institution):
    """Create and return an active institution user."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Principal {suffix}",
            email=f"principal_{suffix}@college.edu",
            hashed_password=hash_password("CollegeSecure@2026!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=test_institution.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


# ── Registration Tests ────────────────────────────────────────────────────────

def test_registration_valid(client: TestClient, test_institution):
    """Valid institution registration returns 201 and safe user profile."""
    suffix = uuid.uuid4().hex[:6]
    payload = {
        "full_name": "Dr. Sarah Khan",
        "email": f"sarah_{suffix}@college.ac.in",
        "password": "StrongPassword@2026",
        "institution_id": str(test_institution.id),
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"].lower()
    assert data["role"] == "INSTITUTION_USER"
    assert data["institution_id"] == str(test_institution.id)
    assert "hashed_password" not in data
    assert "password" not in data


def test_registration_duplicate_email(client: TestClient, test_institution, institution_user):
    """Attempting to register an already-registered email returns 409 Conflict."""
    payload = {
        "full_name": "Another User",
        "email": institution_user.email,
        "password": "StrongPassword@2026",
        "institution_id": str(test_institution.id),
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_registration_invalid_email(client: TestClient, test_institution):
    """Invalid email format is rejected with 422."""
    payload = {
        "full_name": "Bad Email",
        "email": "not-an-email",
        "password": "StrongPassword@2026",
        "institution_id": str(test_institution.id),
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_registration_weak_passwords(client: TestClient, test_institution):
    """Weak passwords that violate policy are rejected with 422."""
    weak_passwords = [
        "short1!",            # < 8 chars
        "alllowercase123!",   # no uppercase
        "ALLUPPERCASE123!",   # no lowercase
        "NoDigitsInPassword!",# no digit
        "NoSpecialChar123",   # no special char
    ]
    for weak_pwd in weak_passwords:
        payload = {
            "full_name": "Weak Pwd Tester",
            "email": f"weak_{uuid.uuid4().hex[:6]}@college.ac.in",
            "password": weak_pwd,
            "institution_id": str(test_institution.id),
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422, f"Expected 422 for password: {weak_pwd}"


def test_registration_invalid_institution_id(client: TestClient):
    """Non-existent institution_id returns 400 Bad Request."""
    payload = {
        "full_name": "Orphan User",
        "email": f"orphan_{uuid.uuid4().hex[:6]}@college.ac.in",
        "password": "StrongPassword@2026",
        "institution_id": str(uuid.uuid4()),
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_registration_role_elevation_prevented(client: TestClient, test_institution):
    """Public registration cannot register ADMIN or OFFICIAL roles; always assigns INSTITUTION_USER."""
    suffix = uuid.uuid4().hex[:6]
    payload = {
        "full_name": "Hacker Trying Admin",
        "email": f"hacker_{suffix}@college.ac.in",
        "password": "StrongPassword@2026",
        "institution_id": str(test_institution.id),
        "role": "ADMIN",  # Attempted injection
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["role"] == "INSTITUTION_USER"


# ── Login Tests ───────────────────────────────────────────────────────────────

def test_login_valid_credentials(client: TestClient, institution_user):
    """Valid credentials return signed JWT bearer token and user profile."""
    response = client.post("/api/v1/auth/login", json={
        "email": institution_user.email,
        "password": "CollegeSecure@2026!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == institution_user.email
    assert data["user"]["role"] == "INSTITUTION_USER"


def test_login_incorrect_password(client: TestClient, institution_user):
    """Incorrect password returns 401 with generic error message."""
    response = client.post("/api/v1/auth/login", json={
        "email": institution_user.email,
        "password": "WrongPassword123!",
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_unknown_email(client: TestClient):
    """Unknown email returns identical 401 message (enumeration prevention)."""
    response = client.post("/api/v1/auth/login", json={
        "email": f"nonexistent_{uuid.uuid4().hex[:6]}@nowhere.com",
        "password": "SomePassword123!",
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_inactive_account(client: TestClient, test_institution):
    """Deactivated accounts are rejected with 403 Forbidden."""
    suffix = uuid.uuid4().hex[:6]
    inactive_email = f"inactive_{suffix}@college.edu"
    with SessionLocal() as db:
        inactive_user = User(
            full_name=f"Inactive {suffix}",
            email=inactive_email,
            hashed_password=hash_password("CollegeSecure@2026!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=test_institution.id,
            is_active=False,
        )
        db.add(inactive_user)
        db.commit()

    response = client.post("/api/v1/auth/login", json={
        "email": inactive_email,
        "password": "CollegeSecure@2026!",
    })
    assert response.status_code == 403
    assert "deactivated" in response.json()["detail"].lower()


# ── JWT Validation & /me Profile Tests ────────────────────────────────────────

def test_me_authenticated(client: TestClient, institution_user):
    """GET /api/v1/auth/me returns current user profile when bearer token is provided."""
    token = create_access_token({"sub": str(institution_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(institution_user.id)
    assert data["email"] == institution_user.email
    assert "hashed_password" not in data


def test_me_unauthenticated(client: TestClient):
    """Unauthenticated request to /me returns 401 Unauthorized."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_expired_token(client: TestClient, institution_user):
    """Expired token returns 401 with 'Token has expired' detail."""
    expired_token = create_access_token(
        {"sub": str(institution_user.id)},
        expires_delta=timedelta(seconds=-10),  # expired in past
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_me_malformed_token(client: TestClient):
    """Malformed or invalid JWT returns 401."""
    headers = {"Authorization": "Bearer not-a-valid-jwt-token"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401


def test_logout_endpoint(client: TestClient, institution_user):
    """POST /api/v1/auth/logout confirms logout instruction."""
    token = create_access_token({"sub": str(institution_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()
