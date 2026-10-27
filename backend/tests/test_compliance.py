"""
AICTE FlowOps — Compliance & Undertakings API Tests (Phase 6)

Validates:
- Institution user creates a compliance record
- Institution user accesses only own records (data isolation)
- Institution user submits compliance
- Official verifies compliance
- Official rejects compliance with a reason
- Institution user cannot verify or reject
- Verified record cannot be submitted again
- Rejected record can be corrected and resubmitted
- Compliance requirement configuration is admin-only
"""

from datetime import date, timedelta
import uuid
import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.compliance import ComplianceRecord
from app.models.compliance_requirement import ComplianceRequirement
from app.models.enums import ComplianceStatus, UserRole
from app.models.institution import Institution
from app.models.user import User
from app.utils.security import create_access_token, hash_password


@pytest.fixture
def institution_a():
    """Create test institution A."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Alpha Institute {suffix}",
            institution_code=f"ALPHA-{suffix}",
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
    """Create test institution B."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Beta Institute {suffix}",
            institution_code=f"BETA-{suffix}",
            institution_type="Pharmacy",
            state="Karnataka",
            district="Bengaluru",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def inst_user_a(institution_a):
    """Institution User for Institution A."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Alpha Dean {suffix}",
            email=f"alpha_{suffix}@inst.edu",
            hashed_password=hash_password("Pass123!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_a.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def inst_user_b(institution_b):
    """Institution User for Institution B."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Beta Dean {suffix}",
            email=f"beta_{suffix}@inst.edu",
            hashed_password=hash_password("Pass123!"),
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
    """AICTE Official User."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"AICTE Official {suffix}",
            email=f"official_{suffix}@aicte.gov.in",
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
    """System Administrator User."""
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"System Admin {suffix}",
            email=f"admin_{suffix}@aicte.gov.in",
            hashed_password=hash_password("AdminPass123!"),
            role=UserRole.ADMIN,
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



class TestComplianceManagement:

    def test_institution_user_creates_compliance_record(self, client: TestClient, inst_user_a, institution_a):
        """Institution user creates a compliance record with server-assigned institution."""
        payload = {
            "compliance_type": "Fire & Safety Undertaking",
            "title": "Annual Fire NOC Submission 2026",
            "description": "Statutory fire safety clearance certificate from municipal authorities",
            "due_date": (date.today() + timedelta(days=45)).isoformat(),
        }
        res = client.post("/api/v1/compliance", json=payload, headers=auth_header(inst_user_a))
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == payload["title"]
        assert data["compliance_type"] == payload["compliance_type"]
        assert data["status"] == ComplianceStatus.PENDING.value
        assert data["institution_id"] == str(institution_a.id)
        assert data["verified_at"] is None
        assert data["verified_by_user_id"] is None

    def test_institution_user_accesses_only_own_records(self, client: TestClient, inst_user_a, inst_user_b):
        """Ensure institution A cannot view institution B's compliance records."""
        # Create record under Institution B
        payload = {
            "compliance_type": "Land Title Deed",
            "title": "Ownership Certificate B",
        }
        create_res = client.post("/api/v1/compliance", json=payload, headers=auth_header(inst_user_b))
        assert create_res.status_code == 201
        record_b_id = create_res.json()["id"]

        # Institution A lists compliance records: B's record must not appear
        list_res = client.get("/api/v1/compliance", headers=auth_header(inst_user_a))
        assert list_res.status_code == 200
        ids = [item["id"] for item in list_res.json()["items"]]
        assert record_b_id not in ids

        # Institution A directly accesses B's record: returns 404 (data isolation)
        detail_res = client.get(f"/api/v1/compliance/{record_b_id}", headers=auth_header(inst_user_a))
        assert detail_res.status_code == 404

    def test_institution_user_submits_compliance(self, client: TestClient, inst_user_a):
        """Institution user can submit a pending compliance record."""
        # Create record
        create_res = client.post(
            "/api/v1/compliance",
            json={"compliance_type": "Faculty Roster", "title": "Faculty List 2026"},
            headers=auth_header(inst_user_a),
        )
        rec_id = create_res.json()["id"]

        # Submit record
        sub_res = client.post(f"/api/v1/compliance/{rec_id}/submit", headers=auth_header(inst_user_a))
        assert sub_res.status_code == 200
        data = sub_res.json()
        assert data["status"] == ComplianceStatus.SUBMITTED.value
        assert data["submitted_at"] is not None

    def test_official_verifies_compliance(self, client: TestClient, inst_user_a, official_user):
        """AICTE official verifies a submitted compliance record with audit history."""
        # Create and submit
        create_res = client.post(
            "/api/v1/compliance",
            json={"compliance_type": "Anti-Ragging", "title": "Anti-Ragging Committee Undertaking"},
            headers=auth_header(inst_user_a),
        )
        rec_id = create_res.json()["id"]
        client.post(f"/api/v1/compliance/{rec_id}/submit", headers=auth_header(inst_user_a))

        # Official verifies
        verify_res = client.post(
            f"/api/v1/compliance/{rec_id}/verify",
            json={"remarks": "Statutory undertaking verified and found complete."},
            headers=auth_header(official_user),
        )
        assert verify_res.status_code == 200
        data = verify_res.json()
        assert data["status"] == ComplianceStatus.VERIFIED.value
        assert data["verified_at"] is not None
        assert data["verified_by_user_id"] == str(official_user.id)

        # Detail endpoint includes verification history
        detail_res = client.get(f"/api/v1/compliance/{rec_id}", headers=auth_header(official_user))
        assert detail_res.status_code == 200
        histories = detail_res.json()["histories"]
        assert len(histories) >= 2  # CREATED, SUBMITTED, VERIFIED
        actions = [h["action"] for h in histories]
        assert "VERIFIED" in actions

    def test_official_rejects_compliance_with_reason(self, client: TestClient, inst_user_a, official_user):
        """Official rejects submission with mandatory statutory explanation."""
        # Create and submit
        create_res = client.post(
            "/api/v1/compliance",
            json={"compliance_type": "Building Safety", "title": "Structural Stability Certificate"},
            headers=auth_header(inst_user_a),
        )
        rec_id = create_res.json()["id"]
        client.post(f"/api/v1/compliance/{rec_id}/submit", headers=auth_header(inst_user_a))

        # Reject without reason fails
        bad_reject = client.post(
            f"/api/v1/compliance/{rec_id}/reject",
            json={"reason": "  "},
            headers=auth_header(official_user),
        )
        assert bad_reject.status_code == 422 or bad_reject.status_code == 400

        # Reject with valid reason
        rejection_reason = "Certificate is expired and lacks signature of certified chartered engineer."
        reject_res = client.post(
            f"/api/v1/compliance/{rec_id}/reject",
            json={"reason": rejection_reason},
            headers=auth_header(official_user),
        )
        assert reject_res.status_code == 200
        data = reject_res.json()
        assert data["status"] == ComplianceStatus.REJECTED.value
        assert data["rejection_reason"] == rejection_reason

    def test_institution_user_cannot_verify_or_reject(self, client: TestClient, inst_user_a):
        """Institution user is forbidden from verifying or rejecting compliance records."""
        create_res = client.post(
            "/api/v1/compliance",
            json={"compliance_type": "Audit", "title": "Balance Sheet 2026"},
            headers=auth_header(inst_user_a),
        )
        rec_id = create_res.json()["id"]
        client.post(f"/api/v1/compliance/{rec_id}/submit", headers=auth_header(inst_user_a))

        # Attempt verification
        v_res = client.post(f"/api/v1/compliance/{rec_id}/verify", json={}, headers=auth_header(inst_user_a))
        assert v_res.status_code == 403

        # Attempt rejection
        r_res = client.post(
            f"/api/v1/compliance/{rec_id}/reject",
            json={"reason": "Self rejection"},
            headers=auth_header(inst_user_a),
        )
        assert r_res.status_code == 403

    def test_verified_record_cannot_be_submitted_again(self, client: TestClient, inst_user_a, official_user):
        """Once verified, record cannot be re-submitted or altered."""
        create_res = client.post(
            "/api/v1/compliance",
            json={"compliance_type": "Land Title", "title": "Land Title Registry"},
            headers=auth_header(inst_user_a),
        )
        rec_id = create_res.json()["id"]
        client.post(f"/api/v1/compliance/{rec_id}/submit", headers=auth_header(inst_user_a))
        client.post(f"/api/v1/compliance/{rec_id}/verify", json={}, headers=auth_header(official_user))

        # Re-submit attempt must fail
        sub_again = client.post(f"/api/v1/compliance/{rec_id}/submit", headers=auth_header(inst_user_a))
        assert sub_again.status_code == 400

        # Update attempt must fail
        up_again = client.patch(
            f"/api/v1/compliance/{rec_id}",
            json={"title": "Updated Title"},
            headers=auth_header(inst_user_a),
        )
        assert up_again.status_code == 400

    def test_rejected_record_can_be_corrected_and_resubmitted(self, client: TestClient, inst_user_a, official_user):
        """Rejected record can have fields updated and then be re-submitted."""
        create_res = client.post(
            "/api/v1/compliance",
            json={"compliance_type": "Water NOC", "title": "Drinking Water Quality"},
            headers=auth_header(inst_user_a),
        )
        rec_id = create_res.json()["id"]
        client.post(f"/api/v1/compliance/{rec_id}/submit", headers=auth_header(inst_user_a))
        client.post(
            f"/api/v1/compliance/{rec_id}/reject",
            json={"reason": "Test report is older than 6 months."},
            headers=auth_header(official_user),
        )

        # Update while REJECTED
        patch_res = client.patch(
            f"/api/v1/compliance/{rec_id}",
            json={"title": "Drinking Water Quality - Revised Report"},
            headers=auth_header(inst_user_a),
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == "Drinking Water Quality - Revised Report"

        # Re-submit
        resubmit_res = client.post(f"/api/v1/compliance/{rec_id}/submit", headers=auth_header(inst_user_a))
        assert resubmit_res.status_code == 200
        assert resubmit_res.json()["status"] == ComplianceStatus.SUBMITTED.value
        assert resubmit_res.json()["rejection_reason"] is None


class TestComplianceRequirementsConfig:

    def test_compliance_requirement_configuration_is_admin_only(
        self,
        client: TestClient,
        admin_user,
        inst_user_a,
        official_user,
    ):
        """Only system admins can create, update, or toggle requirements."""
        req_payload = {
            "name": "Mandatory Barrier-Free Campus Undertaking",
            "compliance_type": "Accessibility",
            "description": "Statutory ramps, braille signage, and accessible facilities",
            "is_required": True,
            "allowed_document_types": ["PWD Compliance Certificate", "Campus Photographs"],
            "default_due_period_days": 30,
            "is_active": True,
        }

        # Institution user cannot create
        inst_res = client.post("/api/v1/compliance-requirements", json=req_payload, headers=auth_header(inst_user_a))
        assert inst_res.status_code == 403

        # Official cannot create (Admin only)
        off_res = client.post("/api/v1/compliance-requirements", json=req_payload, headers=auth_header(official_user))
        assert off_res.status_code == 403

        # Admin can create
        admin_res = client.post("/api/v1/compliance-requirements", json=req_payload, headers=auth_header(admin_user))
        assert admin_res.status_code == 201
        req_id = admin_res.json()["id"]

        # Admin updates requirement
        update_res = client.patch(
            f"/api/v1/compliance-requirements/{req_id}",
            json={"default_due_period_days": 60},
            headers=auth_header(admin_user),
        )
        assert update_res.status_code == 200
        assert update_res.json()["default_due_period_days"] == 60

        # Admin toggles status
        toggle_res = client.patch(
            f"/api/v1/compliance-requirements/{req_id}/status",
            json={"is_active": False},
            headers=auth_header(admin_user),
        )
        assert toggle_res.status_code == 200
        assert toggle_res.json()["is_active"] is False
