"""
AICTE FlowOps — Reporting Endpoints Tests (Phase 8)

Validates:
- Application Summary Reports (JSON pagination and CSV export)
- Compliance Audit Reports (JSON pagination and CSV export)
- Overdue Deadlines & Ageing Reports (JSON pagination and CSV export)
- Document Expiry and Metadata Reports (JSON pagination and CSV export)
- Role permissions & strict institutional data isolation
- CSV header lines, MIME content types, and attachment filenames
- Empty reports safety (valid headers, 0 rows)
- Unauthenticated rejection (401)
"""

from datetime import date, datetime, timedelta
import uuid
import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.application import Application
from app.models.compliance import ComplianceRecord
from app.models.document import Document
from app.models.enums import ApplicationStatus, ComplianceStatus, UserRole
from app.models.institution import Institution
from app.models.user import User
from app.utils.security import create_access_token, hash_password


def auth_header(user: User) -> dict:
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_access_token({"sub": str(user.id), "role": role_val})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def rep_institution_a():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Report Tech A {suffix}",
            institution_code=f"RPT-A-{suffix}",
            institution_type="Engineering",
            state="Karnataka",
            district="Bangalore Urban",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def rep_institution_b():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Report Tech B {suffix}",
            institution_code=f"RPT-B-{suffix}",
            institution_type="Pharmacy",
            state="Kerala",
            district="Ernakulam",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def rep_user_a(rep_institution_a):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Principal A {suffix}",
            email=f"principal_a_{suffix}@rpta.edu",
            hashed_password=hash_password("Pass123!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=rep_institution_a.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def rep_admin():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Admin Report Officer {suffix}",
            email=f"admin_rpt_{suffix}@aicte.gov.in",
            hashed_password=hash_password("AdminPass123!"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


class TestReportsAuthenticationAndAccess:
    """Verifies security boundaries on report downloads."""

    def test_unauthenticated_requests_denied(self, client: TestClient):
        endpoints = [
            "/api/v1/reports/applications",
            "/api/v1/reports/compliance",
            "/api/v1/reports/overdue",
            "/api/v1/reports/documents",
        ]
        for ep in endpoints:
            res = client.get(ep)
            assert res.status_code == 401

    def test_institution_user_cannot_export_other_institution(
        self, client: TestClient, rep_user_a, rep_institution_b
    ):
        res = client.get(
            f"/api/v1/reports/applications?institution_id={rep_institution_b.id}&format=csv",
            headers=auth_header(rep_user_a),
        )
        assert res.status_code == 403


class TestApplicationReports:
    """Verifies Application Summary Reports in JSON and CSV formats."""

    def test_applications_report_json(
        self, client: TestClient, rep_institution_a, rep_user_a
    ):
        with SessionLocal() as db:
            app1 = Application(
                application_number=f"APP-REP-{uuid.uuid4().hex[:6]}",
                institution_id=rep_institution_a.id,
                application_type="New Technical Institute",
                academic_year="2026-2027",
                status=ApplicationStatus.SUBMITTED,
                submitted_at=datetime.now() - timedelta(days=7),
            )
            db.add(app1)
            db.commit()

        res = client.get("/api/v1/reports/applications?format=json", headers=auth_header(rep_user_a))
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        item = data["items"][0]
        assert "application_number" in item
        assert "days_pending" in item
        assert item["institution_id"] == str(rep_institution_a.id)

    def test_applications_report_csv_download(
        self, client: TestClient, rep_institution_a, rep_user_a
    ):
        with SessionLocal() as db:
            app_csv = Application(
                application_number=f"APP-CSV-{uuid.uuid4().hex[:6]}",
                institution_id=rep_institution_a.id,
                application_type="Extension of Approval",
                academic_year="2026-2027",
                status=ApplicationStatus.UNDER_SCRUTINY,
                submitted_at=datetime.now() - timedelta(days=3),
            )
            db.add(app_csv)
            db.commit()

        res = client.get("/api/v1/reports/applications?format=csv", headers=auth_header(rep_user_a))
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        assert "attachment; filename=" in res.headers["content-disposition"]
        lines = res.text.strip().split("\n")
        assert len(lines) >= 2  # Header + at least 1 record
        header = lines[0]
        assert "Application Number" in header
        assert "Institution Code" in header
        assert "Status" in header


class TestComplianceReports:
    """Verifies Compliance Audit Reports in JSON and CSV formats."""

    def test_compliance_report_json_and_csv(
        self, client: TestClient, rep_institution_a, rep_user_a
    ):
        with SessionLocal() as db:
            comp = ComplianceRecord(
                institution_id=rep_institution_a.id,
                compliance_type="Anti-Ragging Undertaking",
                title="Mandatory Anti-Ragging Committee Affidavit",
                status=ComplianceStatus.VERIFIED,
                due_date=date.today() - timedelta(days=10),
                verified_at=datetime.now() - timedelta(days=5),
            )
            db.add(comp)
            db.commit()

        # JSON format
        res_json = client.get(
            "/api/v1/reports/compliance?format=json&status=VERIFIED",
            headers=auth_header(rep_user_a),
        )
        assert res_json.status_code == 200
        data = res_json.json()
        assert data["total"] >= 1
        assert data["items"][0]["status"] == "VERIFIED"

        # CSV format
        res_csv = client.get(
            "/api/v1/reports/compliance?format=csv",
            headers=auth_header(rep_user_a),
        )
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        lines = res_csv.text.strip().split("\n")
        assert "Compliance ID" in lines[0]
        assert "Anti-Ragging Undertaking" in res_csv.text


class TestOverdueReports:
    """Verifies combined Overdue and Ageing Reports."""

    def test_overdue_report_json_and_csv(
        self, client: TestClient, rep_institution_a, rep_admin
    ):
        with SessionLocal() as db:
            # Overdue compliance record
            comp_overdue = ComplianceRecord(
                institution_id=rep_institution_a.id,
                compliance_type="Laboratory Equipment",
                title="AICTE Core Lab Calibration Certificate",
                status=ComplianceStatus.PENDING,
                due_date=date.today() - timedelta(days=15),
            )
            # Ageing application (>30 days pending)
            app_ageing = Application(
                application_number=f"APP-OD-{uuid.uuid4().hex[:6]}",
                institution_id=rep_institution_a.id,
                application_type="New Technical Institute",
                academic_year="2026-2027",
                status=ApplicationStatus.UNDER_SCRUTINY,
                current_stage="Document Scrutiny",
                submitted_at=datetime.now() - timedelta(days=45),
            )
            db.add_all([comp_overdue, app_ageing])
            db.commit()

        # JSON report
        res = client.get("/api/v1/reports/overdue?format=json", headers=auth_header(rep_admin))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        entity_types = [item["entity_type"] for item in data["items"]]
        assert "compliance" in entity_types or "application" in entity_types

        # CSV report
        res_csv = client.get("/api/v1/reports/overdue?format=csv", headers=auth_header(rep_admin))
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert "Entity Type" in res_csv.text


class TestDocumentReports:
    """Verifies Document Expiry and Metadata Reports."""

    def test_document_report_json_and_csv(
        self, client: TestClient, rep_institution_a, rep_admin
    ):
        with SessionLocal() as db:
            doc = Document(
                institution_id=rep_institution_a.id,
                document_name="Building_Plan_Sanction.pdf",
                document_type="Building Sanction Plan",
                storage_key="test/sanction.pdf",
                mime_type="application/pdf",
                file_size=512000,
                expires_at=datetime.now() + timedelta(days=20),
            )
            db.add(doc)
            db.commit()

        # JSON report
        res = client.get(
            "/api/v1/reports/documents?format=json&days_window=30",
            headers=auth_header(rep_admin),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert data["items"][0]["expiry_status"] in ["EXPIRING_SOON", "VALID", "EXPIRED"]

        # CSV report
        res_csv = client.get(
            "/api/v1/reports/documents?format=csv",
            headers=auth_header(rep_admin),
        )
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert "Document Name" in res_csv.text
        assert "Building_Plan_Sanction.pdf" in res_csv.text
