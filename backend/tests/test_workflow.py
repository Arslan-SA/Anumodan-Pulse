"""
AICTE FlowOps — Phase 5 Workflow Engine Test Suite

Validates:
- Active workflow listing and detail retrieval
- Admin workflow configuration and constraint validations (stages, transitions, duplicate prevention)
- Workflow initialization upon application submission
- Rejection of submission when no workflow is configured for the application type
- Valid stage transitions and atomic status/stage updates
- Stage history recording and exited_at tracking
- Invalid transitions (e.g., stage skipping) returning 409 Conflict
- Role-based authorization enforcement on workflow actions
- Institution users forbidden from official actions and cross-institution applications
- Mandatory remarks validation for clarification requests
- Clarification response and history preservation
- Authorized regulatory decisions (approvals/rejections) requiring official roles
- Stale or concurrent action handling
- State integrity verification (failed actions do not modify state)
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.application import Application
from app.models.enums import ApplicationStatus, UserRole
from app.models.institution import Institution
from app.models.stage_history import ApplicationStageHistory
from app.models.user import User
from app.models.workflow_definition import WorkflowDefinition
from app.models.workflow_stage import WorkflowStage
from app.models.workflow_transition import WorkflowTransition
from app.utils.security import create_access_token, hash_password


def auth_header(user: User) -> dict:
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_access_token(data={"sub": str(user.id), "role": role_val})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def institution_a():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Institute A {suffix}",
            institution_code=f"INST-A-{suffix}",
            institution_type="Engineering",
            state="Maharashtra",
            district="Mumbai",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def institution_b():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Institute B {suffix}",
            institution_code=f"INST-B-{suffix}",
            institution_type="Pharmacy",
            state="Karnataka",
            district="Bengaluru",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def user_inst_a(institution_a):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"User Inst A {suffix}",
            email=f"user_a_{suffix}@college.edu",
            hashed_password=hash_password("Pass@123456"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_a.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def user_inst_b(institution_b):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"User Inst B {suffix}",
            email=f"user_b_{suffix}@college.edu",
            hashed_password=hash_password("Pass@123456"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_b.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def official_user():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Official {suffix}",
            email=f"official_{suffix}@aicte.gov.in",
            hashed_password=hash_password("Official@123456"),
            role=UserRole.AICTE_OFFICIAL,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def admin_user():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Admin {suffix}",
            email=f"admin_{suffix}@aicte.gov.in",
            hashed_password=hash_password("Admin@123456"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


# ── 1. Workflow Listing and Detail Inspection ─────────────────────────

def test_list_workflows_admin_and_official(client: TestClient, admin_user, official_user, user_inst_a):
    """Admins and Officials can list workflows; Institution users and unauthenticated are rejected."""
    # Unauthenticated
    res = client.get("/api/v1/workflows")
    assert res.status_code == 401

    # Institution user forbidden
    res = client.get("/api/v1/workflows", headers=auth_header(user_inst_a))
    assert res.status_code == 403

    # Admin access
    res = client.get("/api/v1/workflows", headers=auth_header(admin_user))
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(w["application_type"] == "Extension of Approval" for w in data)

    # Official access
    res = client.get("/api/v1/workflows", headers=auth_header(official_user))
    assert res.status_code == 200


def test_get_workflow_detail(client: TestClient, official_user):
    """Retrieve detailed workflow with stages and transitions."""
    # List to get ID
    list_res = client.get("/api/v1/workflows", headers=auth_header(official_user))
    wf_id = list_res.json()[0]["id"]

    detail_res = client.get(f"/api/v1/workflows/{wf_id}", headers=auth_header(official_user))
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["id"] == wf_id
    assert "stages" in data
    assert len(data["stages"]) >= 1
    assert "transitions" in data
    assert len(data["transitions"]) >= 1

    # Non-existent ID returns 404
    non_existent = str(uuid.uuid4())
    res_404 = client.get(f"/api/v1/workflows/{non_existent}", headers=auth_header(official_user))
    assert res_404.status_code == 404


# ── 2. Admin Workflow Configuration APIs ──────────────────────────────

def test_admin_create_and_configure_workflow(client: TestClient, admin_user, user_inst_a):
    """Admin can create workflow definition, stages, and transitions; non-admin is forbidden."""
    suffix = uuid.uuid4().hex[:6]
    app_type = f"Special Grant {suffix}"

    # Non-admin forbidden
    create_res = client.post("/api/v1/workflows", headers=auth_header(user_inst_a), json={
        "name": f"Workflow {suffix}",
        "application_type": app_type,
    })
    assert create_res.status_code == 403

    # Admin creates workflow
    create_res = client.post("/api/v1/workflows", headers=auth_header(admin_user), json={
        "name": f"Grant Workflow {suffix}",
        "application_type": app_type,
        "description": "Custom grant workflow for institutions.",
    })
    assert create_res.status_code == 201
    wf_data = create_res.json()
    wf_id = wf_data["id"]

    # Admin adds stages
    stage1_res = client.post(f"/api/v1/workflows/{wf_id}/stages", headers=auth_header(admin_user), json={
        "stage_name": "Initial Screening",
        "stage_code": f"SCREEN_{suffix}",
        "sequence_order": 1,
    })
    assert stage1_res.status_code == 201
    stage1_id = stage1_res.json()["id"]

    stage2_res = client.post(f"/api/v1/workflows/{wf_id}/stages", headers=auth_header(admin_user), json={
        "stage_name": "Committee Sanction",
        "stage_code": f"SANCTION_{suffix}",
        "sequence_order": 2,
    })
    assert stage2_res.status_code == 201
    stage2_id = stage2_res.json()["id"]

    # Admin configures transitions
    # 1. Initial transition
    t1_res = client.post(f"/api/v1/workflows/{wf_id}/transitions", headers=auth_header(admin_user), json={
        "from_stage_id": None,
        "to_stage_id": stage1_id,
        "action_name": "SUBMIT",
        "allowed_roles": ["INSTITUTION_USER"],
        "resulting_status": "SUBMITTED",
    })
    assert t1_res.status_code == 201

    # 2. Screening -> Sanction
    t2_res = client.post(f"/api/v1/workflows/{wf_id}/transitions", headers=auth_header(admin_user), json={
        "from_stage_id": stage1_id,
        "to_stage_id": stage2_id,
        "action_name": "PASS_SCREENING",
        "allowed_roles": ["AICTE_OFFICIAL", "ADMIN"],
        "resulting_status": "UNDER_REVIEW",
    })
    assert t2_res.status_code == 201

    # Attempting duplicate transition (same action and source stage) returns 409
    dup_res = client.post(f"/api/v1/workflows/{wf_id}/transitions", headers=auth_header(admin_user), json={
        "from_stage_id": stage1_id,
        "to_stage_id": stage2_id,
        "action_name": "PASS_SCREENING",
        "allowed_roles": ["ADMIN"],
    })
    assert dup_res.status_code == 409

    # Transition with invalid target stage returns 422
    fake_stage = str(uuid.uuid4())
    invalid_res = client.post(f"/api/v1/workflows/{wf_id}/transitions", headers=auth_header(admin_user), json={
        "from_stage_id": stage1_id,
        "to_stage_id": fake_stage,
        "action_name": "INVALID_MOVE",
        "allowed_roles": ["ADMIN"],
    })
    assert invalid_res.status_code == 422


# ── 3. Workflow Initialization on Application Submission ──────────────

def test_workflow_initialization_on_submission(client: TestClient, user_inst_a):
    """Submitting a draft initializes the configured workflow and records initial stage history."""
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_inst_a), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    assert draft_res.status_code == 201
    app_id = draft_res.json()["id"]

    submit_res = client.post(f"/api/v1/applications/{app_id}/submit", headers=auth_header(user_inst_a))
    assert submit_res.status_code == 200
    app_data = submit_res.json()

    assert app_data["status"] == "SUBMITTED"
    assert app_data["submitted_at"] is not None
    assert app_data["current_stage"] == "Scrutiny"

    # Verify workflow state API
    wf_res = client.get(f"/api/v1/applications/{app_id}/workflow", headers=auth_header(user_inst_a))
    assert wf_res.status_code == 200
    wf_data = wf_res.json()
    assert wf_data["current_status"] == "SUBMITTED"
    assert wf_data["current_stage_name"] == "Scrutiny"
    assert len(wf_data["stage_history"]) == 1
    assert wf_data["stage_history"][0]["stage_name"] == "Scrutiny"
    assert wf_data["stage_history"][0]["action_name"] == "SUBMIT"
    assert wf_data["stage_history"][0]["exited_at"] is None


def test_submission_fails_when_no_workflow_configured(client: TestClient, user_inst_a):
    """If no active workflow exists for application_type, submission returns 422 and preserves DRAFT."""
    suffix = uuid.uuid4().hex[:6]
    unconfigured_type = f"Nonexistent Type {suffix}"

    draft_res = client.post("/api/v1/applications", headers=auth_header(user_inst_a), json={
        "application_type": unconfigured_type,
        "academic_year": "2026-2027",
    })
    assert draft_res.status_code == 201
    app_id = draft_res.json()["id"]

    # Attempt submission
    submit_res = client.post(f"/api/v1/applications/{app_id}/submit", headers=auth_header(user_inst_a))
    assert submit_res.status_code == 422
    assert "No active workflow definition configured" in submit_res.json()["detail"]

    # Verify application remains strictly in DRAFT
    get_res = client.get(f"/api/v1/applications/{app_id}", headers=auth_header(user_inst_a))
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "DRAFT"
    assert get_res.json()["submitted_at"] is None


# ── 4. Workflow Actions and State Transitions ──────────────────────────

def test_valid_transition_and_history_logging(client: TestClient, user_inst_a, official_user):
    """AICTE Official moves application from Scrutiny to Evaluation via COMPLETE_SCRUTINY."""
    # 1. Create and submit
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_inst_a), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]
    client.post(f"/api/v1/applications/{app_id}/submit", headers=auth_header(user_inst_a))

    # 2. Official performs COMPLETE_SCRUTINY
    action_res = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(official_user),
        json={"action_name": "COMPLETE_SCRUTINY"},
    )
    assert action_res.status_code == 200
    state = action_res.json()

    assert state["current_stage_name"] == "Evaluation"
    assert state["current_status"] == "UNDER_SCRUTINY"

    # Verify stage history: 2 records (Scrutiny closed, Evaluation open)
    histories = state["stage_history"]
    assert len(histories) == 2

    first_history = histories[0]
    assert first_history["stage_name"] == "Scrutiny"
    assert first_history["exited_at"] is not None

    second_history = histories[1]
    assert second_history["stage_name"] == "Evaluation"
    assert second_history["action_name"] == "COMPLETE_SCRUTINY"
    assert second_history["exited_at"] is None


def test_invalid_transition_rejected_as_conflict(client: TestClient, user_inst_a, official_user):
    """Attempting an action not permitted from the current stage returns 409 Conflict."""
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_inst_a), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]
    client.post(f"/api/v1/applications/{app_id}/submit", headers=auth_header(user_inst_a))

    # Application is in Scrutiny. COMPLETE_EVC is only allowed from EVC stage!
    action_res = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(official_user),
        json={"action_name": "COMPLETE_EVC"},
    )
    assert action_res.status_code == 409
    assert "cannot be performed from stage 'Scrutiny'" in action_res.json()["detail"]

    # Verify stage was NOT altered
    wf_res = client.get(f"/api/v1/applications/{app_id}/workflow", headers=auth_header(user_inst_a))
    assert wf_res.json()["current_stage_name"] == "Scrutiny"


def test_unauthorized_role_attempts_transition(client: TestClient, user_inst_a):
    """Institution user cannot execute official actions like COMPLETE_SCRUTINY."""
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_inst_a), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]
    client.post(f"/api/v1/applications/{app_id}/submit", headers=auth_header(user_inst_a))

    # Institution user tries to complete scrutiny
    action_res = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(user_inst_a),
        json={"action_name": "COMPLETE_SCRUTINY"},
    )
    assert action_res.status_code == 403
    assert "not authorized to perform workflow action" in action_res.json()["detail"]


def test_institution_user_cannot_access_other_institution_workflow(client: TestClient, user_inst_a, user_inst_b):
    """Institution user B cannot view or perform workflow actions on Institution A's application."""
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_inst_a), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]
    client.post(f"/api/v1/applications/{app_id}/submit", headers=auth_header(user_inst_a))

    # User B queries workflow state
    wf_res = client.get(f"/api/v1/applications/{app_id}/workflow", headers=auth_header(user_inst_b))
    assert wf_res.status_code == 404

    # User B attempts action
    action_res = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(user_inst_b),
        json={"action_name": "RESUBMIT_CLARIFICATION"},
    )
    assert action_res.status_code == 404


# ── 5. Remarks Validation, Clarification & Resubmission ───────────────

def test_clarification_return_requires_remarks(client: TestClient, user_inst_a, official_user):
    """Returning for clarification requires mandatory explanatory remarks."""
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_inst_a), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]
    client.post(f"/api/v1/applications/{app_id}/submit", headers=auth_header(user_inst_a))

    # 1. Attempt return without remarks -> 422
    fail_res = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(official_user),
        json={"action_name": "RETURN_FOR_CLARIFICATION", "remarks": ""},
    )
    assert fail_res.status_code == 422
    assert "requires explanatory remarks" in fail_res.json()["detail"]

    # 2. Provide mandatory remarks -> 200
    success_res = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(official_user),
        json={
            "action_name": "RETURN_FOR_CLARIFICATION",
            "remarks": "Please provide the updated land ownership affidavit and fire safety clearance certificate.",
        },
    )
    assert success_res.status_code == 200
    state = success_res.json()
    assert state["current_status"] == "RETURNED_FOR_CLARIFICATION"

    # 3. Institution user responds via RESUBMIT_CLARIFICATION -> 200
    resubmit_res = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(user_inst_a),
        json={
            "action_name": "RESUBMIT_CLARIFICATION",
            "remarks": "Uploaded updated affidavit and NOC from local municipal fire authority.",
        },
    )
    assert resubmit_res.status_code == 200
    state_after = resubmit_res.json()
    assert state_after["current_status"] == "UNDER_SCRUTINY"

    # Verify history chain is completely preserved
    assert len(state_after["stage_history"]) == 3


# ── 6. Regulatory Decision Recording ──────────────────────────────────

def test_regulatory_decision_requires_authorized_official(
    client: TestClient, user_inst_a, official_user, admin_user
):
    """Final decision requires authorized human official; institution users are barred from deciding."""
    # 1. Create and submit
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_inst_a), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]
    client.post(f"/api/v1/applications/{app_id}/submit", headers=auth_header(user_inst_a))

    # Progress through stages to Decision:
    # Scrutiny -> Evaluation
    client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(official_user),
        json={"action_name": "COMPLETE_SCRUTINY"},
    )

    # Evaluation -> Committee Review (skip EVC)
    client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(official_user),
        json={"action_name": "FORWARD_FOR_REVIEW"},
    )

    # Committee Review -> Decision
    client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(official_user),
        json={"action_name": "COMPLETE_REVIEW"},
    )

    # Verify current stage is Decision
    state_res = client.get(f"/api/v1/applications/{app_id}/workflow", headers=auth_header(official_user))
    assert state_res.json()["current_stage_name"] == "Decision"

    # 2. Institution user attempts RECORD_DECISION -> 403
    inst_attempt = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(user_inst_a),
        json={"action_name": "RECORD_DECISION", "remarks": "Approved by college."},
    )
    assert inst_attempt.status_code == 403

    # 3. Official calls RECORD_DECISION without remarks -> 422
    fail_decision = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(official_user),
        json={"action_name": "RECORD_DECISION"},
    )
    assert fail_decision.status_code == 422

    # 4. Official calls RECORD_DECISION with authorized remarks -> 200
    official_decision = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(official_user),
        json={
            "action_name": "RECORD_DECISION",
            "remarks": "Approved by Regional Committee following verification of faculty ratio and building norms.",
        },
    )
    assert official_decision.status_code == 200
    final_state = official_decision.json()
    assert final_state["current_status"] == "APPROVED"

    # 5. Admin can close application -> 200
    close_res = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(admin_user),
        json={"action_name": "CLOSE_APPLICATION"},
    )
    assert close_res.status_code == 200
    assert close_res.json()["current_status"] == "CLOSED"


# ── 7. Concurrency & Stale Workflow Action Handling ───────────────────

def test_stale_workflow_action_rejected_cleanly(client: TestClient, user_inst_a, official_user):
    """When an application advances, stale actions from previous stages return 409 Conflict."""
    draft_res = client.post("/api/v1/applications", headers=auth_header(user_inst_a), json={
        "application_type": "Extension of Approval",
        "academic_year": "2026-2027",
    })
    app_id = draft_res.json()["id"]
    client.post(f"/api/v1/applications/{app_id}/submit", headers=auth_header(user_inst_a))

    # First official action: advance from Scrutiny to Evaluation
    res1 = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(official_user),
        json={"action_name": "COMPLETE_SCRUTINY"},
    )
    assert res1.status_code == 200

    # Stale action: another reviewer/official attempts RETURN_FOR_CLARIFICATION (which applies only to Scrutiny)
    res2 = client.post(
        f"/api/v1/applications/{app_id}/workflow-actions",
        headers=auth_header(official_user),
        json={"action_name": "RETURN_FOR_CLARIFICATION", "remarks": "Stale review feedback"},
    )
    assert res2.status_code == 409
    assert "cannot be performed from stage 'Evaluation'" in res2.json()["detail"]
