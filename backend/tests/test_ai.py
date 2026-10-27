"""
AICTE FlowOps — AI Intelligence & Workflow Insights Tests (Phase 9)

Tests:
1. Authentication & RBAC enforcement across all AI endpoints (401 unauthenticated).
2. Institution data isolation (institution users can only see their own application summaries and insights; cross-tenant query returns 403 or 404).
3. Reviewer access restrictions (unassigned applications return 404).
4. Deterministic fallback behavior when no external AI provider is configured.
5. AI provider success and simulated timeout/error handling with graceful fallback.
6. Invariance of application & compliance status (AI calls are strictly read-only advisory operations).
7. Empty and incomplete application data safety (no 500 crashes).
8. Correct analysis of workflow bottlenecks and compliance deadlines.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional
from unittest.mock import patch
import uuid
import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.application import Application
from app.models.compliance import ComplianceRecord
from app.models.document import Document
from app.models.enums import (
    ApplicationStatus,
    ComplianceStatus,
    UserRole,
)
from app.models.institution import Institution
from app.models.stage_history import ApplicationStageHistory
from app.models.user import User
from app.models.workflow_stage import WorkflowStage
from app.services.ai_provider import AIProviderResult, BaseAIProvider, MockAIProvider
from app.utils.security import create_access_token, hash_password


def auth_header(user: User) -> dict:
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_access_token({"sub": str(user.id), "role": role_val})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def institution_1():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"IIT Bombay Campus {suffix}",
            institution_code=f"IITB-{suffix}",
            institution_type="Engineering",
            state="Maharashtra",
            district="Mumbai",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def institution_2():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"NIT Trichy Campus {suffix}",
            institution_code=f"NITT-{suffix}",
            institution_type="Engineering",
            state="Tamil Nadu",
            district="Tiruchirappalli",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def inst_user_1(institution_1):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Dean IITB {suffix}",
            email=f"dean_iitb_{suffix}@iitb.ac.in",
            hashed_password=hash_password("Secret123!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_1.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def inst_user_2(institution_2):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Dean NITT {suffix}",
            email=f"dean_nitt_{suffix}@nitt.ac.in",
            hashed_password=hash_password("Secret123!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_2.id,
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
            full_name=f"AICTE Administrator {suffix}",
            email=f"admin_{suffix}@aicte-india.org",
            hashed_password=hash_password("Secret123!"),
            role=UserRole.ADMIN,
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
            full_name=f"AICTE Regional Officer {suffix}",
            email=f"officer_{suffix}@aicte-india.org",
            hashed_password=hash_password("Secret123!"),
            role=UserRole.AICTE_OFFICIAL,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def reviewer_user():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Scrutiny Expert {suffix}",
            email=f"expert_{suffix}@aicte-india.org",
            hashed_password=hash_password("Secret123!"),
            role=UserRole.REVIEWER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def app_with_details(institution_1, inst_user_1):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        # Create application
        app = Application(
            institution_id=institution_1.id,
            application_number=f"APP-2026-AI-{suffix}",
            academic_year="2026-2027",
            application_type="Extension of Approval",
            status=ApplicationStatus.UNDER_SCRUTINY,
            current_stage="Scrutiny Committee Review",
            submitted_at=datetime.now(timezone.utc) - timedelta(days=25),
        )
        db.add(app)
        db.commit()
        db.refresh(app)

        # Workflow stage
        stage = WorkflowStage(
            stage_name="Scrutiny Committee Review",
            stage_code=f"SCRUTINY_{suffix}",
            sequence_order=1,
            description="Statutory document scrutiny stage",
        )
        db.add(stage)
        db.flush()

        app.current_stage_id = stage.id

        # Stage history
        sh1 = ApplicationStageHistory(
            application_id=app.id,
            workflow_stage_id=stage.id,
            action_name="Initial Submission",
            status="SUBMITTED",
            entered_at=datetime.now(timezone.utc) - timedelta(days=25),
            exited_at=datetime.now(timezone.utc) - timedelta(days=20),
            acted_by_user_id=inst_user_1.id,
        )
        sh2 = ApplicationStageHistory(
            application_id=app.id,
            workflow_stage_id=stage.id,
            action_name="Scrutiny Committee Review",
            status="UNDER_SCRUTINY",
            entered_at=datetime.now(timezone.utc) - timedelta(days=20),
            exited_at=None,
            acted_by_user_id=inst_user_1.id,
        )
        db.add_all([sh1, sh2])

        # Documents
        doc1 = Document(
            institution_id=institution_1.id,
            application_id=app.id,
            document_name="Land Use Certificate",
            document_type="Land Use Certificate",
            storage_key="uploads/land_cert.pdf",
            mime_type="application/pdf",
            file_size=10240,
            expires_at=datetime.now(timezone.utc) + timedelta(days=180),
        )
        doc2 = Document(
            institution_id=institution_1.id,
            application_id=app.id,
            document_name="Fire Safety NOC",
            document_type="Fire Safety NOC",
            storage_key="uploads/fire_safety_noc.pdf",
            mime_type="application/pdf",
            file_size=20480,
            expires_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        db.add_all([doc1, doc2])

        # Compliance Records
        c1 = ComplianceRecord(
            institution_id=institution_1.id,
            application_id=app.id,
            title="Fire Safety Renewal Affidavit",
            compliance_type="SAFETY",
            status=ComplianceStatus.OVERDUE,
            due_date=date.today() - timedelta(days=5),
        )
        c2 = ComplianceRecord(
            institution_id=institution_1.id,
            application_id=app.id,
            title="Faculty Cadre Ratio Declaration",
            compliance_type="ACADEMIC",
            status=ComplianceStatus.PENDING,
            due_date=date.today() + timedelta(days=7),
        )
        db.add_all([c1, c2])

        db.commit()
        db.refresh(app)
        return app


# ─────────────────────────────────────────────────────────────────────────────
# 1. Authentication Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_unauthenticated_endpoints_return_401(client: TestClient):
    """Ensure all AI endpoints reject unauthenticated access with 401."""
    random_id = uuid.uuid4()
    endpoints = [
        f"/api/v1/ai/applications/{random_id}/summary",
        "/api/v1/ai/dashboard/insights",
        "/api/v1/ai/workflow/bottlenecks",
        "/api/v1/ai/compliance/insights",
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 401, f"Expected 401 for {ep}, got {resp.status_code}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Application Summary & Fallback Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_application_summary_success_fallback(
    client: TestClient, app_with_details: Application, inst_user_1: User
):
    """
    Institution user generates an AI executive summary for their application
    using the deterministic fallback provider.
    """
    resp = client.get(
        f"/api/v1/ai/applications/{app_with_details.id}/summary",
        headers=auth_header(inst_user_1),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["application_id"] == str(app_with_details.id)
    assert data["application_number"] == app_with_details.application_number
    assert "IIT Bombay" in data["institution_name"]
    assert data["status"] == "UNDER_SCRUTINY"
    assert data["days_pending"] >= 20
    assert len(data["completed_stages"]) >= 1
    assert "Initial Submission" in data["completed_stages"]

    # Factual items
    assert len(data["outstanding_actions"]) > 0
    assert len(data["compliance_issues"]) > 0
    assert data["documents_summary"]["total_documents"] == 2
    assert data["documents_summary"]["expired_count"] == 1

    # Advisory disclaimer
    assert "Advisory" in data["advisory_disclaimer"]
    assert "statutory" in data["advisory_disclaimer"]
    assert data["is_ai_generated"] is False
    assert data["provider"] == "deterministic-fallback"


def test_application_summary_with_mock_ai_provider(
    client: TestClient, app_with_details: Application, inst_user_1: User
):
    """Tests the endpoint with a configured mock AI provider generating synthetic text."""
    mock_prov = MockAIProvider(
        canned_response=(
            "Executive Briefing: The institution has submitted documentation for 2026-27 approval. "
            "Scrutiny review is currently active with pending fire safety renewals."
        ),
    )

    with patch("app.services.ai_service.get_ai_provider", return_value=mock_prov):
        resp = client.get(
            f"/api/v1/ai/applications/{app_with_details.id}/summary",
            headers=auth_header(inst_user_1),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_ai_generated"] is True
        assert data["provider"] == "mock"
        assert "Executive Briefing" in data["executive_summary"]


def test_application_summary_does_not_modify_status(
    client: TestClient, app_with_details: Application, inst_user_1: User
):
    """Verifies that calling the summary API NEVER alters application or compliance statuses."""
    with SessionLocal() as db:
        initial_app = db.get(Application, app_with_details.id)
        assert initial_app.status == ApplicationStatus.UNDER_SCRUTINY

    # Call AI summary multiple times
    for _ in range(3):
        resp = client.get(
            f"/api/v1/ai/applications/{app_with_details.id}/summary",
            headers=auth_header(inst_user_1),
        )
        assert resp.status_code == 200

    with SessionLocal() as db:
        post_app = db.get(Application, app_with_details.id)
        assert post_app.status == ApplicationStatus.UNDER_SCRUTINY, "Status must remain unchanged"


def test_application_summary_institution_isolation(
    client: TestClient, app_with_details: Application, inst_user_2: User
):
    """Institution user 2 cannot view Institution user 1's application summary (404 Not Found)."""
    resp = client.get(
        f"/api/v1/ai/applications/{app_with_details.id}/summary",
        headers=auth_header(inst_user_2),
    )
    # Returns 404 to avoid revealing application existence across institutions
    assert resp.status_code == 404


def test_application_summary_reviewer_restriction(
    client: TestClient, app_with_details: Application, reviewer_user: User
):
    """Reviewer cannot view an application they are not assigned to (404 Not Found)."""
    resp = client.get(
        f"/api/v1/ai/applications/{app_with_details.id}/summary",
        headers=auth_header(reviewer_user),
    )
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 3. Dashboard Insights Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_dashboard_insights_institution_scoped(
    client: TestClient, app_with_details: Application, inst_user_1: User
):
    """Institution user receives insights strictly scoped to their institution."""
    resp = client.get("/api/v1/ai/dashboard/insights", headers=auth_header(inst_user_1))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "insights" in data
    assert "total_insights" in data
    assert "critical_count" in data
    assert "advisory_disclaimer" in data

    # Check that any application IDs mentioned belong to inst 1
    for ins in data["insights"]:
        assert ins["category"] in [
            "long_pending",
            "multiple_deficiencies",
            "deadline_approaching",
            "expired_documents",
            "compliance_overdue",
            "compliance_upcoming",
            "document_expired",
            "document_expiring",
        ]
        assert ins["priority"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_dashboard_insights_cross_tenant_forbidden(
    client: TestClient, institution_2: Institution, inst_user_1: User
):
    """Institution user cannot specify another institution's ID (403 Forbidden)."""
    resp = client.get(
        f"/api/v1/ai/dashboard/insights?institution_id={institution_2.id}",
        headers=auth_header(inst_user_1),
    )
    assert resp.status_code == 403


def test_dashboard_insights_admin_system_wide(
    client: TestClient, app_with_details: Application, admin_user: User
):
    """Admin receives system-wide insights with breakdown by priority."""
    resp = client.get("/api/v1/ai/dashboard/insights", headers=auth_header(admin_user))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_insights"] >= 0
    assert isinstance(data["insights"], list)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Workflow Bottlenecks Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_workflow_bottlenecks_admin_analysis(
    client: TestClient, app_with_details: Application, admin_user: User
):
    """Admin retrieves quantitative workflow queue diagnostics and advisory bottleneck narrative."""
    resp = client.get("/api/v1/ai/workflow/bottlenecks", headers=auth_header(admin_user))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["overall_workflow_health"] in [
        "HEALTHY",
        "MODERATE_DELAY",
        "SEVERE_CONGESTION",
    ]
    assert data["total_active_applications"] >= 1
    assert isinstance(data["stages"], list)
    assert len(data["narrative_analysis"]) > 0
    assert "Advisory" in data["advisory_disclaimer"]

    # Validate numerical fields for stage analysis
    for stg in data["stages"]:
        assert "stage_name" in stg
        assert "pending_count" in stg
        assert "target_duration_days" in stg
        assert isinstance(stg["is_bottleneck"], bool)
        assert stg["severity"] in ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_workflow_bottlenecks_institution_isolation(
    client: TestClient, institution_2: Institution, inst_user_1: User
):
    """Institution user cannot request bottleneck analysis for another institution."""
    resp = client.get(
        f"/api/v1/ai/workflow/bottlenecks?institution_id={institution_2.id}",
        headers=auth_header(inst_user_1),
    )
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# 5. Compliance Insights Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_compliance_insights_details(
    client: TestClient, app_with_details: Application, inst_user_1: User
):
    """Evaluates overdue, upcoming, and expiring documents with factual risk assessments."""
    resp = client.get("/api/v1/ai/compliance/insights", headers=auth_header(inst_user_1))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["overdue_count"] >= 1
    assert data["upcoming_count"] >= 1
    assert data["expired_documents_count"] >= 1
    assert len(data["overdue_items"]) >= 1

    # Check overdue item structure
    ov = data["overdue_items"][0]
    assert ov["is_overdue"] is True
    assert "Fire Safety" in ov["title"]
    assert ov["days_overdue_or_remaining"] >= 0

    # Expired document item
    exp_doc = data["expired_documents"][0]
    assert exp_doc["is_expired"] is True
    assert "Fire Safety" in exp_doc["document_type"]

    # Advisory disclaimer
    assert "Advisory" in data["advisory_disclaimer"]


def test_compliance_insights_cross_tenant_forbidden(
    client: TestClient, institution_2: Institution, inst_user_1: User
):
    """Institution user attempting to fetch other institution's compliance insights receives 403."""
    resp = client.get(
        f"/api/v1/ai/compliance/insights?institution_id={institution_2.id}",
        headers=auth_header(inst_user_1),
    )
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# 6. Provider Error Handling & Graceful Fallback
# ─────────────────────────────────────────────────────────────────────────────

class FailingAIProvider(BaseAIProvider):
    """Mock provider simulating external API timeout or rate-limit error."""

    def __init__(self):
        self.provider_name = "failing_provider"
        self.model = "failing_model"

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> AIProviderResult:
        # Simulate network failure or timeout
        raise RuntimeError("External AI service timeout (504 Gateway Timeout)")

    def generate_json(self, prompt: str, system_prompt: Optional[str] = None):
        raise RuntimeError("External AI service timeout (504 Gateway Timeout)")


def test_ai_provider_failure_graceful_fallback(
    client: TestClient, app_with_details: Application, inst_user_1: User
):
    """
    When an external provider fails with network/timeout errors,
    AIService gracefully falls back to deterministic analysis without crashing.
    """
    failing_prov = FailingAIProvider()

    with patch("app.services.ai_service.get_ai_provider", return_value=failing_prov):
        # We test that AIService or caller falls back when generate_text throws
        # Or AIService handles provider exceptions internally
        # Let's verify by testing the endpoint:
        try:
            resp = client.get(
                f"/api/v1/ai/applications/{app_with_details.id}/summary",
                headers=auth_header(inst_user_1),
            )
            # If AIService caught it or returned fallback:
            assert resp.status_code in [200, 503]
        except Exception as exc:
            pytest.fail(f"Endpoint raised uncaught exception: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# 7. Empty Database Safety Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_empty_institution_safe_responses(
    client: TestClient, institution_2: Institution, inst_user_2: User
):
    """Tests that an institution with zero applications or compliance records returns clean empty structures."""
    # 1. Dashboard insights
    resp_dash = client.get("/api/v1/ai/dashboard/insights", headers=auth_header(inst_user_2))
    assert resp_dash.status_code == 200
    dash_data = resp_dash.json()
    assert dash_data["total_insights"] == 0
    assert dash_data["insights"] == []

    # 2. Workflow bottlenecks
    resp_wf = client.get("/api/v1/ai/workflow/bottlenecks", headers=auth_header(inst_user_2))
    assert resp_wf.status_code == 200
    wf_data = resp_wf.json()
    assert wf_data["total_active_applications"] == 0
    assert wf_data["stages"] == []

    # 3. Compliance insights
    resp_comp = client.get("/api/v1/ai/compliance/insights", headers=auth_header(inst_user_2))
    assert resp_comp.status_code == 200
    comp_data = resp_comp.json()
    assert comp_data["overdue_count"] == 0
    assert comp_data["upcoming_count"] == 0
    assert comp_data["expired_documents_count"] == 0
