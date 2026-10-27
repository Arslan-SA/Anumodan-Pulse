"""
AICTE FlowOps — Cloud Object Storage & Render Database Integration Tests

Validates:
1. S3-compatible cloud object storage operations (save, get, delete, exists, presigned URLs).
2. Pure in-memory streaming of document bytes without local filesystem persistence.
3. Strict production safeguards:
   - Forbids SQLite and localhost databases in production mode.
   - Forbids local filesystem storage in production mode.
   - Requires S3 bucket and credentials in production mode.
4. End-to-end Document API integration:
   - Authorized document upload to cloud storage.
   - Authorized document download streamed from cloud storage.
   - Multi-tenant isolation: unauthorized users cannot view metadata or download content.
   - Document deletion removes both cloud object and PostgreSQL metadata.
   - Graceful HTTP 503 error handling during cloud storage outages.
"""

from datetime import datetime, timedelta, timezone
import io
from unittest.mock import MagicMock
import uuid
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.database import SessionLocal
from app.models.enums import UserRole
from app.models.institution import Institution
from app.models.user import User
from app.services.storage import set_storage_backend_override
from app.services.storage.mock_s3 import MockS3StorageBackend
from app.services.storage.s3 import S3StorageBackend
from app.utils.security import create_access_token, hash_password


# ── Helper Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_cloud_storage():
    """Inject an in-memory Mock S3 backend for testing without cloud credentials."""
    backend = MockS3StorageBackend(bucket_name="aicte-test-documents", region="ap-south-1")
    set_storage_backend_override(backend)
    yield backend
    backend.clear()
    set_storage_backend_override(None)


@pytest.fixture
def institution_cloud():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Cloud College {suffix}",
            institution_code=f"CLOUD-{suffix}",
            institution_type="Engineering",
            state="Maharashtra",
            district="Pune",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def other_institution_cloud():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Other College {suffix}",
            institution_code=f"OTHER-{suffix}",
            institution_type="Management",
            state="Karnataka",
            district="Bengaluru",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def user_cloud_inst(institution_cloud):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Dean Cloud {suffix}",
            email=f"dean_{suffix}@cloud-college.edu",
            hashed_password=hash_password("Aicte@Secure2026"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_cloud.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def user_other_inst(other_institution_cloud):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Dean Other {suffix}",
            email=f"dean_{suffix}@other-college.edu",
            hashed_password=hash_password("Aicte@Secure2026"),
            role=UserRole.INSTITUTION_USER,
            institution_id=other_institution_cloud.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


# ── 1. S3StorageBackend Unit Tests (Mocked Boto3 Client) ──────────────────────

def test_s3_backend_save_and_get():
    """Verify S3StorageBackend calls upload_fileobj and download_fileobj on S3 client."""
    mock_boto = MagicMock()
    backend = S3StorageBackend(
        bucket_name="aicte-docs",
        access_key_id="mock_key",
        secret_access_key="mock_secret",
        client=mock_boto,
    )

    sample_bytes = b"%PDF-1.4 Statutory Affidavit Content"
    size = backend.save("institutions/1/affidavit.pdf", sample_bytes, content_type="application/pdf")
    assert size == len(sample_bytes)
    mock_boto.upload_fileobj.assert_called_once()

    # Simulate download_fileobj writing into the target buffer
    def fake_download(bucket, key, target_buf):
        target_buf.write(sample_bytes)

    mock_boto.download_fileobj.side_effect = fake_download
    stream = backend.get("institutions/1/affidavit.pdf")
    assert stream.read() == sample_bytes


def test_s3_backend_delete_and_exists():
    """Verify S3StorageBackend calls delete_object and head_object."""
    mock_boto = MagicMock()
    backend = S3StorageBackend(
        bucket_name="aicte-docs",
        access_key_id="mock_key",
        secret_access_key="mock_secret",
        client=mock_boto,
    )

    # Exists check (success)
    mock_boto.head_object.return_value = {"ContentLength": 1024}
    assert backend.exists("institutions/1/doc.pdf") is True

    # Exists check (404 NoSuchKey)
    mock_boto.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
    )
    assert backend.exists("institutions/1/missing.pdf") is False

    # Delete
    assert backend.delete("institutions/1/doc.pdf") is True
    mock_boto.delete_object.assert_called_once_with(Bucket="aicte-docs", Key="institutions/1/doc.pdf")


def test_s3_backend_presigned_download_url():
    """Verify S3StorageBackend generates pre-signed URL."""
    mock_boto = MagicMock()
    mock_boto.generate_presigned_url.return_value = "https://aicte-docs.s3.amazonaws.com/doc.pdf?signed=1"
    backend = S3StorageBackend(
        bucket_name="aicte-docs",
        access_key_id="mock_key",
        secret_access_key="mock_secret",
        client=mock_boto,
    )

    url = backend.get_download_url("institutions/1/doc.pdf", expires_in_seconds=1800)
    assert url == "https://aicte-docs.s3.amazonaws.com/doc.pdf?signed=1"
    mock_boto.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "aicte-docs", "Key": "institutions/1/doc.pdf"},
        ExpiresIn=1800,
    )


# ── 2. Production Security & Infrastructure Safeguards ────────────────────────

def test_production_rejects_sqlite_database():
    """Production mode must reject SQLite database URLs."""
    s = Settings(
        app_env="production",
        database_url="sqlite:///./test.db",
        jwt_secret_key="a" * 32,
        storage_backend="s3",
        s3_bucket_name="aicte-prod",
        s3_access_key_id="key",
        s3_secret_access_key="secret",
    )
    with pytest.raises(ValueError, match="SQLite is forbidden"):
        s.validate_production_security()


def test_production_rejects_localhost_database():
    """Production mode must reject local database instances."""
    s = Settings(
        app_env="production",
        database_url="postgresql://user:pass@localhost:5432/aicte",
        jwt_secret_key="a" * 32,
        storage_backend="s3",
        s3_bucket_name="aicte-prod",
        s3_access_key_id="key",
        s3_secret_access_key="secret",
    )
    with pytest.raises(ValueError, match="local database host is forbidden"):
        s.validate_production_security()


def test_production_rejects_local_filesystem_storage():
    """Production mode must reject local filesystem storage backend."""
    s = Settings(
        app_env="production",
        database_url="postgresql://user:pass@ep-cool.render.com:5432/aicte_db",
        jwt_secret_key="a" * 32,
        storage_backend="local",
    )
    with pytest.raises(ValueError, match="local filesystem storage is forbidden"):
        s.validate_production_security()


def test_production_rejects_missing_s3_credentials():
    """Production mode must fail if S3 bucket or credentials are missing."""
    s = Settings(
        app_env="production",
        database_url="postgresql://user:pass@ep-cool.render.com:5432/aicte_db",
        jwt_secret_key="a" * 32,
        storage_backend="s3",
        s3_bucket_name="",
        s3_access_key_id="some_key",
        s3_secret_access_key="some_secret",
    )
    with pytest.raises(ValueError, match="S3_BUCKET_NAME must be configured"):
        s.validate_production_security()


def test_production_accepts_render_postgres_and_s3():
    """Accepts valid Render PostgreSQL URL and S3 cloud storage credentials."""
    s = Settings(
        app_env="production",
        database_url="postgres://aicte_user:secure_pwd@dpg-render-postgres.render.com/aicte_flowops",
        jwt_secret_key="x9#K2$vL8!mP0@qR5*tW3&zY7^bC1%eF4(jH6)uN",
        storage_backend="s3",
        s3_bucket_name="aicte-flowops-prod-documents",
        s3_access_key_id="AKIA_RENDER_PROD_12345",
        s3_secret_access_key="SECRET_RENDER_PROD_67890",
        s3_region="ap-south-1",
    )
    # Must not raise
    s.validate_production_security()
    assert s.normalized_database_url.startswith("postgresql://")


# ── 3. End-to-End Cloud Document API Integration ─────────────────────────────

def test_cloud_document_upload_download_delete_lifecycle(
    client: TestClient,
    mock_cloud_storage: MockS3StorageBackend,
    user_cloud_inst: User,
    user_other_inst: User,
):
    """
    Test full document lifecycle with cloud object storage:
    - Upload streams to cloud storage without local disk persistence.
    - Metadata saved to PostgreSQL.
    - Owner downloads streamed from cloud storage.
    - Multi-tenant isolation: unauthorized user gets 404.
    - Deletion removes object from cloud storage and PostgreSQL.
    """
    token_owner = create_access_token({"sub": str(user_cloud_inst.id), "email": user_cloud_inst.email, "role": "INSTITUTION_USER"})
    token_other = create_access_token({"sub": str(user_other_inst.id), "email": user_other_inst.email, "role": "INSTITUTION_USER"})

    # 1. Upload valid statutory PDF
    pdf_content = b"%PDF-1.4\nLand Title Deed 2026 Statutory Document\n%%EOF"
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("land_title.pdf", io.BytesIO(pdf_content), "application/pdf")},
        data={"document_name": "Land Title 2026", "document_type": "Land Record"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert upload_res.status_code == 201
    doc_info = upload_res.json()
    doc_id = doc_info["id"]

    # Verify bytes stored in cloud storage (not on local disk)
    assert len(mock_cloud_storage._objects) == 1
    stored_key = list(mock_cloud_storage._objects.keys())[0]
    stored_bytes, stored_mime = mock_cloud_storage._objects[stored_key]
    assert stored_bytes == pdf_content
    assert stored_mime == "application/pdf"

    # 2. Owner downloads document
    down_res = client.get(
        f"/api/v1/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert down_res.status_code == 200
    assert down_res.content == pdf_content
    assert "attachment" in down_res.headers.get("Content-Disposition", "")

    # 3. Multi-tenant isolation check: Other institution user denied
    unauth_res = client.get(
        f"/api/v1/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {token_other}"},
    )
    assert unauth_res.status_code == 404

    # 4. Anonymous user denied
    anon_res = client.get(f"/api/v1/documents/{doc_id}/download")
    assert anon_res.status_code == 401

    # 5. Delete document
    del_res = client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert del_res.status_code == 204

    # Verify cloud object and database metadata deleted
    assert stored_key not in mock_cloud_storage._objects
    get_after_del = client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert get_after_del.status_code == 404


def test_cloud_storage_outage_returns_503(
    client: TestClient,
    mock_cloud_storage: MockS3StorageBackend,
    user_cloud_inst: User,
):
    """Verify graceful HTTP 503 handling when cloud object storage experiences an outage."""
    token_owner = create_access_token({"sub": str(user_cloud_inst.id), "email": user_cloud_inst.email, "role": "INSTITUTION_USER"})

    # Simulate cloud storage outage
    mock_cloud_storage.simulate_outage = True

    pdf_content = b"%PDF-1.4\nBuilding Safety Certificate\n%%EOF"
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("safety.pdf", io.BytesIO(pdf_content), "application/pdf")},
        data={"document_name": "Safety Cert", "document_type": "Safety"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert upload_res.status_code == 503
    assert "Cloud document storage service is currently unavailable" in upload_res.json()["detail"]
