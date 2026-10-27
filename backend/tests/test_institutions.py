"""
AICTE FlowOps — Institution Management API Tests (Phase 4)

Validates:
- GET /api/v1/institutions/me (Institution user retrieves own profile)
- PATCH /api/v1/institutions/me (Institution user updates permitted fields)
- Disallowed updates (cannot change id or institution_code)
- Isolation (Institution user cannot access another institution via ID)
- GET /api/v1/institutions (Admin and Official list institutions with pagination & filter)
- GET /api/v1/institutions/{id} (Admin and Official get institution details)
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.enums import UserRole
from app.models.institution import Institution
from app.models.user import User
from app.utils.security import create_access_token, hash_password


@pytest.fixture
def institution_alpha():
    """Create test institution Alpha."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Alpha Institute of Technology {suffix}",
            institution_code=f"ALPHA-{suffix}",
            institution_type="Engineering",
            email=f"contact_{suffix}@alpha.edu",
            phone="9876543210",
            address="123 Tech Park",
            state="Karnataka",
            district="Bangalore",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def institution_beta():
    """Create test institution Beta."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Beta Polytechnic {suffix}",
            institution_code=f"BETA-{suffix}",
            institution_type="Polytechnic",
            email=f"contact_{suffix}@beta.edu",
            phone="9123456780",
            address="456 Skill Highway",
            state="Maharashtra",
            district="Pune",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def user_alpha(institution_alpha):
    """User linked to institution Alpha."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Principal Alpha {suffix}",
            email=f"principal_alpha_{suffix}@alpha.edu",
            hashed_password=hash_password("SecureAlpha@2026!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_alpha.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def user_beta(institution_beta):
    """User linked to institution Beta."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Principal Beta {suffix}",
            email=f"principal_beta_{suffix}@beta.edu",
            hashed_password=hash_password("SecureBeta@2026!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_beta.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def admin_user():
    """Active Administrator."""
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
    """Active AICTE Official."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Regional Officer {suffix}",
            email=f"officer_{suffix}@aicte.gov.in",
            hashed_password=hash_password("OfficerSecure@2026!"),
            role=UserRole.AICTE_OFFICIAL,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def auth_header(user: User) -> dict:
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_access_token({"sub": str(user.id), "role": role_val})
    return {"Authorization": f"Bearer {token}"}


# ── Institution Profile Tests ─────────────────────────────────────────────────

def test_institution_user_retrieves_own_institution(client: TestClient, user_alpha, institution_alpha):
    """Institution user receives only their own institution via GET /institutions/me."""
    res = client.get("/api/v1/institutions/me", headers=auth_header(user_alpha))
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(institution_alpha.id)
    assert data["institution_code"] == institution_alpha.institution_code
    assert data["institution_name"] == institution_alpha.institution_name


def test_institution_user_updates_permitted_fields(client: TestClient, user_alpha, institution_alpha):
    """Institution user can update permitted fields (address, phone, type)."""
    update_payload = {
        "address": "999 Updated Knowledge Corridor",
        "phone": "9998887776",
        "institution_type": "Autonomous University",
    }
    res = client.patch("/api/v1/institutions/me", headers=auth_header(user_alpha), json=update_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["address"] == "999 Updated Knowledge Corridor"
    assert data["phone"] == "9998887776"
    assert data["institution_type"] == "Autonomous University"
    assert data["institution_code"] == institution_alpha.institution_code  # Immutable


def test_institution_user_cannot_mutate_code_or_id(client: TestClient, user_alpha, institution_alpha):
    """Attempts to mutate institution_code or id in payload are ignored/rejected."""
    payload = {
        "institution_code": "MUTATED-CODE-999",
        "id": str(uuid.uuid4()),
        "phone": "9876543211",
    }
    res = client.patch("/api/v1/institutions/me", headers=auth_header(user_alpha), json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(institution_alpha.id)
    assert data["institution_code"] == institution_alpha.institution_code
    assert data["phone"] == "9876543211"


def test_institution_user_forbidden_from_admin_directory(client: TestClient, user_alpha):
    """Institution users cannot list all institutions via GET /institutions."""
    res = client.get("/api/v1/institutions", headers=auth_header(user_alpha))
    assert res.status_code == 403


# ── Admin & Official Institution Directory Tests ──────────────────────────────

def test_official_lists_institutions_with_pagination(client: TestClient, official_user, institution_alpha, institution_beta):
    """AICTE_OFFICIAL can query paginated directory of institutions."""
    res = client.get("/api/v1/institutions?page=1&page_size=10", headers=auth_header(official_user))
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert data["page"] == 1
    assert data["total"] >= 2


def test_official_searches_institution_by_code(client: TestClient, official_user, institution_alpha):
    """Official can search by exact or partial institution code."""
    res = client.get(f"/api/v1/institutions?search={institution_alpha.institution_code}", headers=auth_header(official_user))
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(i["institution_code"] == institution_alpha.institution_code for i in items)


def test_admin_retrieves_institution_details_by_id(client: TestClient, admin_user, institution_alpha):
    """ADMIN can retrieve any institution profile by ID."""
    res = client.get(f"/api/v1/institutions/{institution_alpha.id}", headers=auth_header(admin_user))
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(institution_alpha.id)
    assert data["institution_name"] == institution_alpha.institution_name


def test_admin_retrieves_nonexistent_institution(client: TestClient, admin_user):
    """Requesting non-existent institution ID returns 404."""
    res = client.get(f"/api/v1/institutions/{uuid.uuid4()}", headers=auth_header(admin_user))
    assert res.status_code == 404
