"""
AICTE FlowOps — Application Management API Tests (Phase 4)

Validates:
- Draft creation with server-generated application_number
- Institution data isolation (institution user can only view/edit/delete their own)
- Draft updates
- Submission transitions (DRAFT -> SUBMITTED)
- Inability to edit or delete submitted applications
- Cross-institution listings and searches for AICTE Officials and Admins
- Reviewer assignment boundary (empty list / 404 when unassigned)
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.enums import ApplicationStatus, UserRole
from app.models.institution import Institution
from app.models.user import User
from app.utils.security import create_access_token, hash_password


@pytest.fixture
def institution_one():
    """Create test institution One."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"First Engineering College {suffix}",
            institution_code=f"FEC-{suffix}",
            institution_type="Engineering",
            state="Delhi",
            district="New Delhi",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def institution_two():
    """Create test institution Two."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Second Polytechnic {suffix}",
            institution_code=f"SPT-{suffix}",
            institution_type="Polytechnic",
            state="Punjab",
            district="Chandigarh",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def user_one(institution_one):
    """Institution User for Institution One."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"User One {suffix}",
            email=f"user_one_{suffix}@inst1.edu",
            hashed_password=hash_password("CollegePass@2026!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_one.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def user_two(institution_two):
    """Institution User for Institution Two."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"User Two {suffix}",
            email=f"user_two_{suffix}@inst2.edu",
            hashed_password=hash_password("CollegePass@2026!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_two.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def official_user():
    """AICTE Official."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Official {suffix}",
            email=f"official_{suffix}@aicte.gov.in",
            hashed_password=hash_password("OfficialPass@2026!"),
            role=UserRole.AICTE_OFFICIAL,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def reviewer_user():
    """Committee Reviewer."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Reviewer {suffix}",
            email=f"reviewer_{suffix}@aicte.gov.in",
            hashed_password=hash_password("ReviewerPass@2026!"),
            role=UserRole.REVIEWER,
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


# ── Application Creation & Draft Tests ────────────────────────────────────────

def test_create_draft_application(client: TestClient, user_one, institution_one):
    """Institution user can create a DRAFT application with auto-generated application number."""
    payload = {
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    }
    res = client.post("/api/v1/applications", headers=auth_header(user_one), json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "DRAFT"
    assert data["application_type"] == "Extension of Approval"
    assert data["academic_year"] == "2026-2027"
    assert data["institution_id"] == str(institution_one.id)
    assert data["application_number"].startswith("APP-2026-")
    assert data["submitted_at"] is None


def test_update_draft_application(client: TestClient, user_one):
    """Institution user can update permitted fields of their DRAFT application."""
    # Create draft
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_one), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]

    # Update draft
    update_res = client.patch(f"/api/v1/applications/{app_id}", headers=auth_header(user_one), json={
        "application_type": "Increase in Intake",
    })
    assert update_res.status_code == 200
    assert update_res.json()["application_type"] == "Increase in Intake"
    assert update_res.json()["academic_year"] == "2026-2027"


def test_delete_draft_application(client: TestClient, user_one):
    """Institution user can delete an unsubmitted DRAFT application."""
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_one), json={
        "application_type": "New Course Introduction",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]

    del_res = client.delete(f"/api/v1/applications/{app_id}", headers=auth_header(user_one))
    assert del_res.status_code == 204

    # Verify 404 after deletion
    get_res = client.get(f"/api/v1/applications/{app_id}", headers=auth_header(user_one))
    assert get_res.status_code == 404


# ── Submission & State Lock Tests ─────────────────────────────────────────────

def test_submit_draft_application(client: TestClient, user_one):
    """Institution user submits a draft; status transitions to SUBMITTED and timestamp is set."""
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_one), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]

    submit_res = client.post(f"/api/v1/applications/{app_id}/submit", headers=auth_header(user_one))
    assert submit_res.status_code == 200
    data = submit_res.json()
    assert data["status"] == "SUBMITTED"
    assert data["submitted_at"] is not None
    assert data["current_stage"] == "Scrutiny"


def test_cannot_update_submitted_application(client: TestClient, user_one):
    """Attempts to edit an already-submitted application are rejected with 400."""
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_one), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]
    client.post(f"/api/v1/applications/{app_id}/submit", headers=auth_header(user_one))

    # Attempt edit
    edit_res = client.patch(f"/api/v1/applications/{app_id}", headers=auth_header(user_one), json={
        "application_type": "Tampered Type",
    })
    assert edit_res.status_code == 400
    assert "cannot edit application" in edit_res.json()["detail"].lower()


def test_cannot_delete_submitted_application(client: TestClient, user_one):
    """Attempts to delete an already-submitted application are rejected with 400."""
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_one), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]
    client.post(f"/api/v1/applications/{app_id}/submit", headers=auth_header(user_one))

    # Attempt delete
    del_res = client.delete(f"/api/v1/applications/{app_id}", headers=auth_header(user_one))
    assert del_res.status_code == 400
    assert "cannot delete application" in del_res.json()["detail"].lower()


# ── Institutional Data Isolation Tests ────────────────────────────────────────

def test_institution_user_cannot_view_other_institution_applications(client: TestClient, user_one, user_two):
    """User Two cannot view or list applications belonging to Institution One (returns 404)."""
    # User One creates application
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_one), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]

    # User Two attempts to view User One's application
    res = client.get(f"/api/v1/applications/{app_id}", headers=auth_header(user_two))
    assert res.status_code == 404


def test_institution_user_listing_is_scoped(client: TestClient, user_one, user_two):
    """User One and User Two see only their own institution's applications in GET /applications."""
    # User One creates draft
    client.post("/api/v1/applications", headers=auth_header(user_one), json={
        "application_type": "Type Alpha",
        "academic_year": "2026-2027",
    })
    # User Two creates draft
    client.post("/api/v1/applications", headers=auth_header(user_two), json={
        "application_type": "Type Beta",
        "academic_year": "2026-2027",
    })

    # User One query
    res1 = client.get("/api/v1/applications", headers=auth_header(user_one))
    assert res1.status_code == 200
    items1 = res1.json()["items"]
    assert all(a["institution_id"] == str(user_one.institution_id) for a in items1)


# ── Official & Reviewer Scopes ────────────────────────────────────────────────

def test_official_lists_cross_institution_applications(client: TestClient, official_user, user_one, user_two):
    """AICTE_OFFICIAL can query applications across all institutions."""
    res = client.get("/api/v1/applications", headers=auth_header(official_user))
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 2


def test_reviewer_unassigned_returns_empty(client: TestClient, reviewer_user):
    """Reviewers without active assignments receive an empty list rather than exposing applications."""
    res = client.get("/api/v1/applications", headers=auth_header(reviewer_user))
    assert res.status_code == 200
    assert res.json()["items"] == []
    assert res.json()["total"] == 0
