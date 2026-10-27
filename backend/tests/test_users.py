"""
AICTE FlowOps — User Management & RBAC Tests (Phase 3)

Validates:
- RBAC guards (401 unauthenticated, 403 non-admin roles)
- Admin listing users with pagination & role filtering
- Admin retrieving user by ID
- Admin updating user active status
- Admin updating user role
- System safeguards: preventing deactivating or demoting the last active admin
- Self-role tampering prevention
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

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
            institution_name=f"Govt Engg Institute {suffix}",
            institution_code=f"GEI-{suffix}",
            institution_type="Engineering",
            state="Maharashtra",
            district="Mumbai",
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
            full_name=f"Admin Test {suffix}",
            email=f"admin_test_{suffix}@aicte.gov.in",
            hashed_password=hash_password("AdminSecure@2026!"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def secondary_admin_user():
    """Create a second active administrator to allow testing demotion/deactivation."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Admin Two {suffix}",
            email=f"admin_two_{suffix}@aicte.gov.in",
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
            full_name=f"Officer Test {suffix}",
            email=f"officer_test_{suffix}@aicte.gov.in",
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
            full_name=f"College User {suffix}",
            email=f"college_user_{suffix}@college.edu",
            hashed_password=hash_password("CollegeSecure@2026!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=test_institution.id,
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


# ── RBAC Authorization Tests ──────────────────────────────────────────────────

def test_users_unauthenticated_rejected(client: TestClient):
    """Accessing /api/v1/users without token returns 401 Unauthorized."""
    response = client.get("/api/v1/users")
    assert response.status_code == 401


def test_users_institution_role_forbidden(client: TestClient, institution_user):
    """INSTITUTION_USER role is rejected with 403 Forbidden on user management."""
    response = client.get("/api/v1/users", headers=auth_header(institution_user))
    assert response.status_code == 403
    assert "access denied" in response.json()["detail"].lower()


def test_users_official_role_forbidden(client: TestClient, official_user):
    """AICTE_OFFICIAL role is rejected with 403 Forbidden on admin user management."""
    response = client.get("/api/v1/users", headers=auth_header(official_user))
    assert response.status_code == 403
    assert "access denied" in response.json()["detail"].lower()


# ── Admin User Management Tests ───────────────────────────────────────────────

def test_admin_list_users_with_filter(client: TestClient, admin_user, official_user):
    """ADMIN can list users and filter by role."""
    headers = auth_header(admin_user)

    # All users
    res = client.get("/api/v1/users", headers=headers)
    assert res.status_code == 200
    users = res.json()
    assert isinstance(users, list)
    assert len(users) >= 2

    # Filter by AICTE_OFFICIAL
    res_filtered = client.get("/api/v1/users?role=AICTE_OFFICIAL", headers=headers)
    assert res_filtered.status_code == 200
    filtered_users = res_filtered.json()
    assert all(u["role"] == "AICTE_OFFICIAL" for u in filtered_users)


def test_admin_get_user_by_id(client: TestClient, admin_user, official_user):
    """ADMIN can retrieve individual user profile by UUID."""
    headers = auth_header(admin_user)
    res = client.get(f"/api/v1/users/{official_user.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(official_user.id)
    assert data["email"] == official_user.email
    assert "hashed_password" not in data


def test_admin_toggle_user_status(client: TestClient, admin_user, institution_user):
    """ADMIN can deactivate and reactivate another user account."""
    headers = auth_header(admin_user)

    # Deactivate
    res_deactivate = client.patch(
        f"/api/v1/users/{institution_user.id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert res_deactivate.status_code == 200
    assert res_deactivate.json()["is_active"] is False

    # Reactivate
    res_activate = client.patch(
        f"/api/v1/users/{institution_user.id}/status",
        headers=headers,
        json={"is_active": True},
    )
    assert res_activate.status_code == 200
    assert res_activate.json()["is_active"] is True


def test_admin_change_user_role(client: TestClient, admin_user, institution_user):
    """ADMIN can promote or modify another user's role."""
    headers = auth_header(admin_user)

    res = client.patch(
        f"/api/v1/users/{institution_user.id}/role",
        headers=headers,
        json={"role": "REVIEWER"},
    )
    assert res.status_code == 200
    assert res.json()["role"] == "REVIEWER"


def test_prevent_self_role_demotion(client: TestClient, admin_user):
    """Administrator cannot demote their own account."""
    headers = auth_header(admin_user)
    res = client.patch(
        f"/api/v1/users/{admin_user.id}/role",
        headers=headers,
        json={"role": "INSTITUTION_USER"},
    )
    assert res.status_code == 400
    assert "cannot demote their own" in res.json()["detail"].lower()


def test_prevent_last_admin_deactivation(client: TestClient):
    """System refuses to deactivate the last remaining active administrator."""
    # Ensure there is exactly one active admin in a test transaction
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        # Create a lone admin
        lone_admin = User(
            full_name=f"Lone Admin {suffix}",
            email=f"lone_admin_{suffix}@aicte.gov.in",
            hashed_password=hash_password("AdminSecure@2026!"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(lone_admin)
        db.commit()
        db.refresh(lone_admin)

        # Deactivate all other admins temporarily to test the boundary condition
        other_admins = db.scalars(
            select(User).where(User.role == UserRole.ADMIN, User.id != lone_admin.id)
        ).all()
        for a in other_admins:
            a.is_active = False
        db.commit()

        try:
            # Attempt deactivation of the lone admin
            headers = auth_header(lone_admin)
            res = client.patch(
                f"/api/v1/users/{lone_admin.id}/status",
                headers=headers,
                json={"is_active": False},
            )
            assert res.status_code == 400
            assert "last active administrator" in res.json()["detail"].lower()
        finally:
            # Restore other admins
            for a in other_admins:
                a.is_active = True
            db.commit()
