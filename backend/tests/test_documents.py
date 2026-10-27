"""
AICTE FlowOps — Document Management API Tests (Phase 6)

Validates:
- Authorized document upload with genuine MIME/magic bytes
- Rejection of invalid file extensions and mismatched MIME bytes
- Oversized file rejection
- Institution user cannot access another institution's document
- Unauthorized download is denied
- Document expiry query with date window
- Protected document deletion rejection (when linked to VERIFIED compliance)
- Sanitized document metadata (no storage credentials or private server paths exposed)
"""

from datetime import datetime, timedelta, timezone
import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.compliance import ComplianceRecord
from app.models.enums import ComplianceStatus, UserRole
from app.models.institution import Institution
from app.models.user import User
from app.utils.security import create_access_token, hash_password


@pytest.fixture
def institution_1():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"College One {suffix}",
            institution_code=f"C1-{suffix}",
            institution_type="Engineering",
            state="Delhi",
            district="Central",
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
            institution_name=f"College Two {suffix}",
            institution_code=f"C2-{suffix}",
            institution_type="Management",
            state="Haryana",
            district="Gurugram",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def user_inst_1(institution_1):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Principal One {suffix}",
            email=f"principal1_{suffix}@c1.edu",
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
def user_inst_2(institution_2):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Principal Two {suffix}",
            email=f"principal2_{suffix}@c2.edu",
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
            full_name=f"AICTE Evaluator {suffix}",
            email=f"evaluator_{suffix}@aicte.gov.in",
            hashed_password=hash_password("GovPass123!"),
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



def make_sample_pdf(content: str = "AICTE Statutory Land Document") -> bytes:
    """Generate minimal valid PDF byte sequence starting with %PDF-."""
    return f"%PDF-1.4\n1 0 obj\n<< /Title ({content}) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF".encode("utf-8")


class TestDocumentManagement:

    def test_authorized_document_upload(self, client: TestClient, user_inst_1, institution_1):
        """Institution user can upload a valid PDF document with metadata."""
        pdf_bytes = make_sample_pdf("Land Title Deed 2026")
        files = {
            "file": ("land_deed.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
        }
        data = {
            "document_name": "Land Title Deed 2026",
            "document_type": "Land Document",
        }
        res = client.post("/api/v1/documents", files=files, data=data, headers=auth_header(user_inst_1))
        assert res.status_code == 201
        doc_data = res.json()
        assert doc_data["document_name"] == "Land Title Deed 2026"
        assert doc_data["document_type"] == "Land Document"
        assert doc_data["mime_type"] == "application/pdf"
        assert doc_data["institution_id"] == str(institution_1.id)
        assert doc_data["file_size"] == len(pdf_bytes)

        # Ensure internal storage key and credentials are not in response
        assert "storage_key" not in doc_data
        assert "aws_access_key" not in str(doc_data)
        assert "storage_path" not in str(doc_data)

    def test_invalid_file_type_rejected(self, client: TestClient, user_inst_1):
        """Reject unsupported file extensions (e.g., .exe) and forged headers."""
        # 1. Disallowed extension
        files = {
            "file": ("malware.exe", io.BytesIO(b"MZ\x90\x00\x03"), "application/octet-stream"),
        }
        res = client.post(
            "/api/v1/documents",
            files=files,
            data={"document_name": "Script", "document_type": "Other"},
            headers=auth_header(user_inst_1),
        )
        assert res.status_code == 400
        assert "Unsupported file format" in res.json()["detail"]

        # 2. .pdf extension but fake contents (not matching %PDF)
        fake_files = {
            "file": ("fake.pdf", io.BytesIO(b"Plain text not a real pdf"), "application/pdf"),
        }
        res2 = client.post(
            "/api/v1/documents",
            files=fake_files,
            data={"document_name": "Fake", "document_type": "Other"},
            headers=auth_header(user_inst_1),
        )
        assert res2.status_code == 400
        assert "File content does not match expected format" in res2.json()["detail"]

    def test_oversized_file_rejected(self, client: TestClient, user_inst_1):
        """Reject file exceeding configured max size limit."""
        # Generate 16MB of data starting with %PDF-
        huge_bytes = b"%PDF-1.4\n" + b"X" * (16 * 1024 * 1024)
        files = {
            "file": ("huge.pdf", io.BytesIO(huge_bytes), "application/pdf"),
        }
        res = client.post(
            "/api/v1/documents",
            files=files,
            data={"document_name": "Too Large", "document_type": "Land"},
            headers=auth_header(user_inst_1),
        )
        assert res.status_code == 400
        assert "exceeds maximum allowed size" in res.json()["detail"]

    def test_institution_user_cannot_access_another_institution_document(
        self,
        client: TestClient,
        user_inst_1,
        user_inst_2,
    ):
        """Institution 2 cannot view metadata or download Institution 1's documents."""
        # Upload as Institution 1
        pdf_bytes = make_sample_pdf("Private Financials Inst 1")
        files = {"file": ("financials.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        upload_res = client.post(
            "/api/v1/documents",
            files=files,
            data={"document_name": "Audit 2026", "document_type": "Financial Audit"},
            headers=auth_header(user_inst_1),
        )
        assert upload_res.status_code == 201
        doc_id = upload_res.json()["id"]

        # Institution 2 accesses metadata -> 404
        meta_res = client.get(f"/api/v1/documents/{doc_id}", headers=auth_header(user_inst_2))
        assert meta_res.status_code == 404

        # Institution 2 attempts download -> 404
        down_res = client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_header(user_inst_2))
        assert down_res.status_code == 404

    def test_unauthorized_download_denied(self, client: TestClient, user_inst_1):
        """Anonymous requests to download endpoints are rejected."""
        pdf_bytes = make_sample_pdf("Test Document")
        files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        upload_res = client.post(
            "/api/v1/documents",
            files=files,
            data={"document_name": "Test Doc", "document_type": "General"},
            headers=auth_header(user_inst_1),
        )
        assert upload_res.status_code == 201
        doc_id = upload_res.json()["id"]

        # Anonymous download attempt
        anon_res = client.get(f"/api/v1/documents/{doc_id}/download")
        assert anon_res.status_code == 401

    def test_document_download_by_owner_and_official(
        self,
        client: TestClient,
        user_inst_1,
        official_user,
    ):
        """Owner and authorized official can successfully download the document."""
        pdf_bytes = make_sample_pdf("Affiliation Certificate")
        files = {"file": ("affil.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        upload_res = client.post(
            "/api/v1/documents",
            files=files,
            data={"document_name": "Affiliation Certificate", "document_type": "University Affiliation"},
            headers=auth_header(user_inst_1),
        )
        assert upload_res.status_code == 201
        doc_id = upload_res.json()["id"]

        # Owner downloads
        owner_down = client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_header(user_inst_1))
        assert owner_down.status_code == 200
        assert owner_down.content.startswith(b"%PDF-")

        # Official downloads
        off_down = client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_header(official_user))
        assert off_down.status_code == 200
        assert off_down.content.startswith(b"%PDF-")

    def test_document_expiry_query(
        self,
        client: TestClient,
        user_inst_1,
        user_inst_2,
        official_user,
    ):
        """Query documents expiring within a given window."""
        # 1. Document expiring in 10 days (within 30 days window)
        exp_soon = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        files1 = {"file": ("soon.pdf", io.BytesIO(make_sample_pdf("Expiring Soon")), "application/pdf")}
        client.post(
            "/api/v1/documents",
            files=files1,
            data={"document_name": "Fire Safety 2026", "document_type": "NOC", "expires_at": exp_soon},
            headers=auth_header(user_inst_1),
        )

        # 2. Document expiring in 100 days (outside 30 days window)
        exp_late = (datetime.now(timezone.utc) + timedelta(days=100)).isoformat()
        files2 = {"file": ("late.pdf", io.BytesIO(make_sample_pdf("Expiring Late")), "application/pdf")}
        client.post(
            "/api/v1/documents",
            files=files2,
            data={"document_name": "Building Plan", "document_type": "NOC", "expires_at": exp_late},
            headers=auth_header(user_inst_1),
        )

        # Query with 30 days window as owner
        res_30 = client.get("/api/v1/documents/expiring?days_window=30", headers=auth_header(user_inst_1))
        assert res_30.status_code == 200
        items_30 = res_30.json()
        names_30 = [item["document_name"] for item in items_30]
        assert "Fire Safety 2026" in names_30
        assert "Building Plan" not in names_30

        # Query with 120 days window includes both
        res_120 = client.get("/api/v1/documents/expiring?days_window=120", headers=auth_header(user_inst_1))
        assert res_120.status_code == 200
        names_120 = [item["document_name"] for item in res_120.json()]
        assert "Building Plan" in names_120

        # Institution 2 cannot see Institution 1's expiring documents
        res_other = client.get("/api/v1/documents/expiring?days_window=30", headers=auth_header(user_inst_2))
        assert res_other.status_code == 200
        other_names = [item["document_name"] for item in res_other.json()]
        assert "Fire Safety 2026" not in other_names

        # Official can see expiring documents across institutions
        off_res = client.get("/api/v1/documents/expiring?days_window=30", headers=auth_header(official_user))
        assert off_res.status_code == 200
        off_names = [item["document_name"] for item in off_res.json()]
        assert "Fire Safety 2026" in off_names

    def test_protected_document_deletion_rejected(
        self,
        client: TestClient,
        user_inst_1,
        official_user,
    ):
        """Documents attached to a VERIFIED compliance record cannot be deleted."""
        # 1. Create compliance record
        cr_res = client.post(
            "/api/v1/compliance",
            json={"compliance_type": "Land Title", "title": "Verified Land Deed"},
            headers=auth_header(user_inst_1),
        )
        cr_id = cr_res.json()["id"]

        # 2. Upload document attached to compliance record
        pdf_bytes = make_sample_pdf("Verified Title Deed")
        files = {"file": ("title.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        data = {
            "document_name": "Official Title Deed",
            "document_type": "Land Deed",
            "compliance_record_id": cr_id,
        }
        up_res = client.post("/api/v1/documents", files=files, data=data, headers=auth_header(user_inst_1))
        assert up_res.status_code == 201
        doc_id = up_res.json()["id"]

        # 3. Submit and verify compliance record
        client.post(f"/api/v1/compliance/{cr_id}/submit", headers=auth_header(user_inst_1))
        client.post(f"/api/v1/compliance/{cr_id}/verify", json={}, headers=auth_header(official_user))

        # 4. Attempt to delete document attached to VERIFIED record: rejected
        del_res = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_header(user_inst_1))
        assert del_res.status_code == 400
        assert "Cannot delete a document that is part of a VERIFIED" in del_res.json()["detail"]

    def test_unprotected_document_deletion_succeeds(self, client: TestClient, user_inst_1):
        """Unprotected document can be safely deleted by its owner without cascading entities."""
        files = {"file": ("temp.pdf", io.BytesIO(make_sample_pdf("Draft")), "application/pdf")}
        up_res = client.post(
            "/api/v1/documents",
            files=files,
            data={"document_name": "Draft Note", "document_type": "Note"},
            headers=auth_header(user_inst_1),
        )
        doc_id = up_res.json()["id"]

        # Delete document
        del_res = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_header(user_inst_1))
        assert del_res.status_code == 204

        # Verify it no longer exists
        get_res = client.get(f"/api/v1/documents/{doc_id}", headers=auth_header(user_inst_1))
        assert get_res.status_code == 404
