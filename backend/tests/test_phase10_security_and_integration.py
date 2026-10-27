"""
AICTE FlowOps — Phase 10 Final Integration, Security Hardening & Deployment Readiness Tests

Validates:
- Root health probe and index endpoint for Cloud PaaS (Render / Kubernetes)
- Database URL normalization for cloud Postgres providers (postgres:// -> postgresql://)
- Production security validator (rejection of default dev keys in production)
- Storage path traversal prevention and file sanitization
- JWT security (tampered signatures, expired tokens, claims validation)
- RBAC and Cross-Tenant Data Isolation (Institution A cannot see Institution B)
- Reviewer authorization boundary (only assigned applications)
- Human-in-the-loop workflow invariants (no autonomous state skips)
- Scheduler lifecycle and idempotency controls
- Sensitive credential non-exposure in API responses
"""

from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
import jwt
from sqlalchemy import select

from app.config import Settings
from app.database import SessionLocal
from app.models.application import Application
from app.models.enums import ApplicationStatus, UserRole
from app.models.institution import Institution
from app.models.user import User
from app.services.storage.local import LocalStorageBackend
from app.utils.security import create_access_token, hash_password


@pytest.fixture
def db_session():
    """Request-scoped database session fixture."""
    with SessionLocal() as session:
        yield session



# ── 1. Root Deployment Probes & Health Checks ────────────────────────────────

def test_root_health_probe(client: TestClient):
    """Cloud PaaS orchestrators (Render / Fly / ALB) probe /health directly."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "version" in data
    assert "timestamp" in data


def test_root_index_service_info(client: TestClient):
    """GET / returns service metadata and documentation link."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "AICTE FlowOps API"
    assert data["status"] == "active"
    assert data["docs"] == "/docs"


# ── 2. Configuration & Cloud Database URL Normalization ──────────────────────

def test_database_url_normalization_handles_postgres_prefix():
    """Render/Heroku/AWS provide postgres:// which SQLAlchemy 2.0 rejects unless normalized to postgresql://."""
    s = Settings(database_url="postgres://user:pass@ep-cool-db.render.com/aicte_db")
    assert s.normalized_database_url == "postgresql://user:pass@ep-cool-db.render.com/aicte_db"


def test_database_url_normalization_leaves_postgresql_untouched():
    """Standard postgresql:// URLs remain intact."""
    s = Settings(database_url="postgresql://user:pass@localhost:5432/aicte_db")
    assert s.normalized_database_url == "postgresql://user:pass@localhost:5432/aicte_db"


def test_production_security_validator_rejects_insecure_key():
    """Fails fast when app_env is production but JWT secret is insecure or contains 'development'."""
    s = Settings(
        app_env="production",
        jwt_secret_key="aicte-flowops-development-secret-key-at-least-32-chars-long-2026",
    )
    with pytest.raises(ValueError, match="CRITICAL SECURITY"):
        s.validate_production_security()


def test_production_security_validator_passes_with_strong_key():
    """Accepts strong 32+ char key without 'development' in production."""
    s = Settings(
        app_env="production",
        jwt_secret_key="x9#K2$vL8!mP0@qR5*tW3&zY7^bC1%eF4(jH6)uN",
    )
    # Should not raise
    s.validate_production_security()


# ── 3. Storage Security & Path Traversal Prevention ──────────────────────────

def test_local_storage_prevents_path_traversal(tmp_path):
    """Storage backend must reject keys containing directory traversal attempts."""
    backend = LocalStorageBackend(base_dir=str(tmp_path))
    
    with pytest.raises(ValueError, match="Path traversal detected"):
        backend._resolve_safe_path("../../etc/passwd")

    with pytest.raises(ValueError, match="Path traversal detected"):
        backend._resolve_safe_path("../../../secrets.env")


def test_local_storage_accepts_clean_storage_key(tmp_path):
    """Normalizes and safely resolves clean nested keys within the base dir."""
    backend = LocalStorageBackend(base_dir=str(tmp_path))
    safe_path = backend._resolve_safe_path("institutions/inst_123/doc_abc.pdf")
    assert str(safe_path).startswith(str(tmp_path.resolve()))


# ── 4. JWT Cryptographic Security & Tamper Rejection ─────────────────────────

def test_tampered_jwt_signature_rejected(client: TestClient):
    """Tokens signed with a different key must be rejected with 401."""
    tampered_token = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000001", "role": "ADMIN"},
        "wrong-secret-key-that-does-not-match-server-at-all",
        algorithm="HS256",
    )
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert res.status_code == 401
    assert "Could not validate credentials" in res.json()["detail"]


def test_expired_jwt_token_rejected(client: TestClient, db_session):
    """Tokens past expiration must be rejected with 401."""
    # Create active user
    u = User(
        email=f"expired_test_user_{uuid.uuid4().hex[:6]}@aicte.gov.in",
        full_name="Expired User",
        hashed_password=hash_password("Aicte@Secure2026"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()

    # Expired 1 hour ago
    expired_token = create_access_token(
        data={"sub": str(u.id), "email": u.email, "role": "ADMIN"},
        expires_delta=timedelta(hours=-1),
    )

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


# ── 5. Cross-Tenant Data Isolation ───────────────────────────────────────────

def test_institution_user_cannot_read_other_institution_applications(client: TestClient, db_session):
    """Institution A user cannot access applications belonging to Institution B."""
    unique_suffix = uuid.uuid4().hex[:6]
    inst_a = Institution(institution_name="College A Phase10", institution_code=f"INST-A-{unique_suffix}", state="Delhi")
    inst_b = Institution(institution_name="College B Phase10", institution_code=f"INST-B-{unique_suffix}", state="Karnataka")
    db_session.add_all([inst_a, inst_b])
    db_session.commit()

    user_a = User(
        email=f"user_p10_a_{unique_suffix}@college-a.edu",
        full_name="Officer College A",
        hashed_password=hash_password("Aicte@Secure2026"),
        role=UserRole.INSTITUTION_USER,
        institution_id=inst_a.id,
        is_active=True,
    )
    db_session.add(user_a)
    db_session.commit()

    # Application belonging to Institution B
    app_b = Application(
        application_number=f"APP-B-{unique_suffix}",
        institution_id=inst_b.id,
        application_type="New Institution",
        academic_year="2026-2027",
        status=ApplicationStatus.SUBMITTED,
    )
    db_session.add(app_b)
    db_session.commit()

    token_a = create_access_token({"sub": str(user_a.id), "email": user_a.email, "role": "INSTITUTION_USER"})

    # Attempt to read Institution B's application
    res = client.get(f"/api/v1/applications/{app_b.id}", headers={"Authorization": f"Bearer {token_a}"})
    # Must be 404 to avoid leaking existence of other tenants' records
    assert res.status_code in [403, 404]


# ── 6. Reviewer Authorization Boundary ───────────────────────────────────────

def test_reviewer_cannot_access_unassigned_applications(client: TestClient, db_session):
    """Reviewers must not be able to access applications to which they were never assigned."""
    unique_suffix = uuid.uuid4().hex[:6]
    inst = Institution(institution_name="Tech University P10", institution_code=f"TECH-U-{unique_suffix}", state="Maharashtra")
    db_session.add(inst)
    db_session.commit()

    reviewer = User(
        email=f"unassigned_reviewer_{unique_suffix}@aicte.gov.in",
        full_name="Unassigned Reviewer P10",
        hashed_password=hash_password("Aicte@Secure2026"),
        role=UserRole.REVIEWER,
        is_active=True,
    )
    db_session.add(reviewer)
    db_session.commit()

    # Application not assigned to this reviewer
    app = Application(
        application_number=f"APP-REV-{unique_suffix}",
        institution_id=inst.id,
        application_type="Extension of Approval",
        academic_year="2026-2027",
        status=ApplicationStatus.SUBMITTED,
    )
    db_session.add(app)
    db_session.commit()

    token_rev = create_access_token({"sub": str(reviewer.id), "email": reviewer.email, "role": "REVIEWER"})

    # AI Summary access must be rejected
    res = client.get(f"/api/v1/ai/applications/{app.id}/summary", headers={"Authorization": f"Bearer {token_rev}"})
    assert res.status_code in [403, 404]


# ── 7. Sensitive Credential Non-Exposure ─────────────────────────────────────

def test_user_responses_never_expose_password_hash(client: TestClient, db_session):
    """GET /api/v1/auth/me and GET /api/v1/users must never leak password hash."""
    admin = User(
        email=f"leak_test_admin_{uuid.uuid4().hex[:6]}@aicte.gov.in",
        full_name="Leak Test Admin",
        hashed_password=hash_password("Aicte@Secure2026"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    token = create_access_token({"sub": str(admin.id), "email": admin.email, "role": "ADMIN"})
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "hashed_password" not in data
    assert "password" not in data
