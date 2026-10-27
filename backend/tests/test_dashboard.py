"""
AICTE FlowOps — Dashboard Analytics & Reporting Tests (Phase 8)

Validates:
- Role-specific dashboard overview endpoints and data isolation
- Institution users can only view their own institution's data
- Admin / Official users view system-wide data and can filter by institution
- Reviewers receive isolated view (unassigned returns valid zeroed/empty response)
- Cross-institution parameter tampering by institution users is rejected (403)
- Application analytics, workflow ageing buckets, and compliance fulfillments
- Alert analytics and supervisor escalation histories
- Empty database state safety (zeroes / empty lists, no 500 crashes)
"""

from datetime import date, datetime, timedelta
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
    NotificationPriority,
    NotificationStatus,
    NotificationType,
    UserRole,
)
from app.models.escalation_history import EscalationHistory
from app.models.institution import Institution
from app.models.notification import Notification
from app.models.stage_history import ApplicationStageHistory
from app.models.user import User
from app.models.workflow_stage import WorkflowStage
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
            institution_name=f"Institute One {suffix}",
            institution_code=f"INST-1-{suffix}",
            institution_type="Engineering",
            state="Maharashtra",
            district="Pune",
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
            institution_name=f"Institute Two {suffix}",
            institution_code=f"INST-2-{suffix}",
            institution_type="Polytechnic",
            state="Delhi",
            district="New Delhi",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def institution_user_1(institution_1):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Dean One {suffix}",
            email=f"dean1_{suffix}@inst1.edu",
            hashed_password=hash_password("Pass123!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_1.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def institution_user_2(institution_2):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Dean Two {suffix}",
            email=f"dean2_{suffix}@inst2.edu",
            hashed_password=hash_password("Pass123!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_2.id,
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
            email=f"officer_{suffix}@aicte.gov.in",
            hashed_password=hash_password("GovPass123!"),
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
            full_name=f"Director Admin {suffix}",
            email=f"admin_{suffix}@aicte.gov.in",
            hashed_password=hash_password("AdminPass123!"),
            role=UserRole.ADMIN,
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
            full_name=f"Expert Reviewer {suffix}",
            email=f"reviewer_{suffix}@aicte.gov.in",
            hashed_password=hash_password("ReviewerPass123!"),
            role=UserRole.REVIEWER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


class TestDashboardAuthenticationAndAuthorization:
    """Verifies that authentication and role boundaries are strictly enforced."""

    def test_unauthenticated_requests_rejected(self, client: TestClient):
        endpoints = [
            "/api/v1/dashboard/overview",
            "/api/v1/dashboard/applications",
            "/api/v1/dashboard/workflow",
            "/api/v1/dashboard/compliance",
            "/api/v1/dashboard/alerts",
        ]
        for ep in endpoints:
            res = client.get(ep)
            assert res.status_code == 401

    def test_institution_user_cannot_access_other_institution_analytics(
        self, client: TestClient, institution_user_1, institution_2
    ):
        """Institution 1 user attempting to pass institution_2 ID must receive 403 Forbidden."""
        res = client.get(
            f"/api/v1/dashboard/overview?institution_id={institution_2.id}",
            headers=auth_header(institution_user_1),
        )
        assert res.status_code == 403
        assert "not permitted" in res.json()["detail"]

    def test_reviewer_cannot_pass_institution_id(
        self, client: TestClient, reviewer_user, institution_1
    ):
        """Reviewers cannot query institution-scoped metrics."""
        res = client.get(
            f"/api/v1/dashboard/overview?institution_id={institution_1.id}",
            headers=auth_header(reviewer_user),
        )
        assert res.status_code == 403


class TestDashboardOverviewAndIsolation:
    """Verifies aggregated metrics and institutional data isolation."""

    def test_institution_isolation_in_overview(
        self, client: TestClient, institution_1, institution_2, institution_user_1, official_user
    ):
        """Verify that Institution 1 sees strictly its own records, while Official sees all."""
        with SessionLocal() as db:
            # Seed 2 applications for Inst 1 (1 Submitted, 1 Clarification Required)
            app1 = Application(
                application_number=f"APP-{uuid.uuid4().hex[:6]}",
                institution_id=institution_1.id,
                application_type="New Technical Institute",
                academic_year="2026-2027",
                status=ApplicationStatus.SUBMITTED,
                submitted_at=datetime.now() - timedelta(days=5),
            )
            app2 = Application(
                application_number=f"APP-{uuid.uuid4().hex[:6]}",
                institution_id=institution_1.id,
                application_type="Extension of Approval",
                academic_year="2026-2027",
                status=ApplicationStatus.RETURNED_FOR_CLARIFICATION,
                submitted_at=datetime.now() - timedelta(days=12),
            )
            # Seed 1 application for Inst 2 (Approved)
            app3 = Application(
                application_number=f"APP-{uuid.uuid4().hex[:6]}",
                institution_id=institution_2.id,
                application_type="New Technical Institute",
                academic_year="2026-2027",
                status=ApplicationStatus.APPROVED,
                submitted_at=datetime.now() - timedelta(days=20),
            )
            # Seed Compliance records
            c1 = ComplianceRecord(
                institution_id=institution_1.id,
                compliance_type="Land & Building",
                title="Title Deed Verification",
                status=ComplianceStatus.PENDING,
                due_date=date.today() + timedelta(days=5),
            )
            c2 = ComplianceRecord(
                institution_id=institution_2.id,
                compliance_type="Faculty Cadre Ratio",
                title="Faculty Norms Compliance",
                status=ComplianceStatus.VERIFIED,
                due_date=date.today() - timedelta(days=2),
            )
            db.add_all([app1, app2, app3, c1, c2])
            db.commit()

        # Institution 1 overview request
        res1 = client.get("/api/v1/dashboard/overview", headers=auth_header(institution_user_1))
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["role"] == UserRole.INSTITUTION_USER.value
        assert data1["institution_id"] == str(institution_1.id)
        assert data1["application_summary"]["total"] >= 2
        assert data1["application_summary"]["returned_for_clarification"] >= 1
        assert data1["application_summary"]["requires_action"] >= 1
        assert data1["compliance_summary"]["total"] >= 1
        assert data1["compliance_summary"]["upcoming_deadlines"] >= 1

        # Official overview request (system-wide)
        res_off = client.get("/api/v1/dashboard/overview", headers=auth_header(official_user))
        assert res_off.status_code == 200
        data_off = res_off.json()
        assert data_off["role"] == UserRole.AICTE_OFFICIAL.value
        assert data_off["application_summary"]["total"] >= 3

        # Official filtered to Institution 1
        res_filtered = client.get(
            f"/api/v1/dashboard/overview?institution_id={institution_1.id}",
            headers=auth_header(official_user),
        )
        assert res_filtered.status_code == 200
        data_filtered = res_filtered.json()
        assert data_filtered["institution_id"] == str(institution_1.id)
        assert data_filtered["application_summary"]["total"] >= 2

    def test_reviewer_overview_returns_clean_empty_metrics(
        self, client: TestClient, reviewer_user
    ):
        """Reviewers receive zeroed application metrics without errors."""
        res = client.get("/api/v1/dashboard/overview", headers=auth_header(reviewer_user))
        assert res.status_code == 200
        data = res.json()
        assert data["role"] == UserRole.REVIEWER.value
        assert data["application_summary"]["total"] == 0
        assert data["recent_activity"] == []


class TestDetailedAnalyticsEndpoints:
    """Verifies detailed analytics: applications, workflow ageing, compliance, and alerts."""

    def test_application_analytics_with_date_filters(
        self, client: TestClient, institution_1, institution_user_1
    ):
        start = (date.today() - timedelta(days=30)).isoformat()
        end = date.today().isoformat()
        res = client.get(
            f"/api/v1/dashboard/applications?start_date={start}&end_date={end}",
            headers=auth_header(institution_user_1),
        )
        assert res.status_code == 200
        data = res.json()
        assert "total_applications" in data
        assert "status_distribution" in data
        assert "application_type_distribution" in data
        assert "academic_year_distribution" in data
        assert "submission_trends" in data
        assert isinstance(data["approval_rate"], float)

    def test_application_analytics_invalid_date_range_rejected(
        self, client: TestClient, institution_user_1
    ):
        res = client.get(
            "/api/v1/dashboard/applications?start_date=2026-12-31&end_date=2026-01-01",
            headers=auth_header(institution_user_1),
        )
        assert res.status_code == 400
        assert "start_date cannot be later" in res.json()["detail"]

    def test_workflow_analytics_and_ageing_buckets(
        self, client: TestClient, institution_1, admin_user
    ):
        with SessionLocal() as db:
            # Create active application pending 40 days
            app_ageing = Application(
                application_number=f"APP-{uuid.uuid4().hex[:6]}",
                institution_id=institution_1.id,
                application_type="New Technical Institute",
                academic_year="2026-2027",
                status=ApplicationStatus.UNDER_SCRUTINY,
                current_stage="Scrutiny Committee Review",
                submitted_at=datetime.now() - timedelta(days=40),
            )
            # Create completed application to test processing duration
            app_done = Application(
                application_number=f"APP-{uuid.uuid4().hex[:6]}",
                institution_id=institution_1.id,
                application_type="New Technical Institute",
                academic_year="2026-2027",
                status=ApplicationStatus.APPROVED,
                submitted_at=datetime.now() - timedelta(days=60),
                updated_at=datetime.now() - timedelta(days=10),
            )
            db.add_all([app_ageing, app_done])
            db.commit()

        res = client.get("/api/v1/dashboard/workflow", headers=auth_header(admin_user))
        assert res.status_code == 200
        data = res.json()
        assert data["total_active_in_workflow"] >= 1
        assert "stage_distribution" in data
        assert "ageing_buckets" in data
        assert data["ageing_buckets"]["days_30_to_60"] >= 1
        assert data["average_processing_duration_days"] is not None
        assert data["completed_count"] >= 1

    def test_compliance_analytics_and_document_expiry_buckets(
        self, client: TestClient, institution_1, admin_user
    ):
        with SessionLocal() as db:
            # Expiring document in 15 days
            doc1 = Document(
                institution_id=institution_1.id,
                document_name="Occupancy_Cert.pdf",
                document_type="Occupancy Certificate",
                storage_key="test/occupancy.pdf",
                mime_type="application/pdf",
                file_size=204800,
                expires_at=datetime.now() + timedelta(days=15),
            )
            # Expired document
            doc2 = Document(
                institution_id=institution_1.id,
                document_name="Expired_NOC.pdf",
                document_type="Fire NOC",
                storage_key="test/fire_noc.pdf",
                mime_type="application/pdf",
                file_size=102400,
                expires_at=datetime.now() - timedelta(days=5),
            )
            db.add_all([doc1, doc2])
            db.commit()

        res = client.get("/api/v1/dashboard/compliance", headers=auth_header(admin_user))
        assert res.status_code == 200
        data = res.json()
        assert "total_records" in data
        assert "fulfilment_rate" in data
        assert "document_expiry_breakdown" in data
        assert data["document_expiry_breakdown"]["expiring_30_days"] >= 1
        assert data["document_expiry_breakdown"]["expired"] >= 1

    def test_alerts_analytics_endpoint(
        self, client: TestClient, institution_1, admin_user, official_user
    ):
        with SessionLocal() as db:
            notif = Notification(
                recipient_user_id=official_user.id,
                notification_type=NotificationType.APPLICATION_SUBMITTED,
                title="New Application Submitted",
                message="Application submitted by institute",
                priority=NotificationPriority.HIGH,
                status=NotificationStatus.UNREAD,
            )
            esc = EscalationHistory(
                entity_type="compliance",
                entity_id=uuid.uuid4(),
                rule_name="Critical Safety Undertaking Breach",
                escalation_level=2,
                escalated_to_role="ADMIN",
                escalated_to_user_id=admin_user.id,
                reason="Statutory deadline elapsed without submission",
            )
            db.add_all([notif, esc])
            db.commit()

        res = client.get("/api/v1/dashboard/alerts", headers=auth_header(admin_user))
        assert res.status_code == 200
        data = res.json()
        assert "priority_breakdown" in data
        assert "type_breakdown" in data
        assert data["escalations_count"] >= 1
        assert len(data["recent_escalations"]) >= 1


class TestEmptyDatabaseResponses:
    """Verifies that an empty database or fresh institution returns clean defaults without crashes."""

    def test_empty_institution_dashboard(self, client: TestClient):
        suffix = uuid.uuid4().hex[:6]
        with SessionLocal() as db:
            empty_inst = Institution(
                institution_name=f"Fresh Empty Institute {suffix}",
                institution_code=f"EMPTY-{suffix}",
                institution_type="Management",
                state="Goa",
                district="North Goa",
            )
            db.add(empty_inst)
            db.commit()
            db.refresh(empty_inst)

            empty_user = User(
                full_name=f"Empty Dean {suffix}",
                email=f"empty_{suffix}@inst.edu",
                hashed_password=hash_password("Pass123!"),
                role=UserRole.INSTITUTION_USER,
                institution_id=empty_inst.id,
                is_active=True,
            )
            db.add(empty_user)
            db.commit()
            db.refresh(empty_user)

        res = client.get("/api/v1/dashboard/overview", headers=auth_header(empty_user))
        assert res.status_code == 200
        data = res.json()
        assert data["application_summary"]["total"] == 0
        assert data["application_summary"]["approved"] == 0
        assert data["compliance_summary"]["total"] == 0
        assert data["alerts_summary"]["unread"] == 0
        assert data["recent_activity"] == []

        res_app = client.get("/api/v1/dashboard/applications", headers=auth_header(empty_user))
        assert res_app.status_code == 200
        app_data = res_app.json()
        assert app_data["total_applications"] == 0
        assert app_data["approval_rate"] == 0.0

        res_wf = client.get("/api/v1/dashboard/workflow", headers=auth_header(empty_user))
        assert res_wf.status_code == 200
        wf_data = res_wf.json()
        assert wf_data["total_active_in_workflow"] == 0
        assert wf_data["average_processing_duration_days"] is None
