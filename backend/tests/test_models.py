"""
AICTE FlowOps — Model Schema & Relationship Tests (Phase 2)

Validates:
- Model imports and metadata registration
- Live database schema inspection (tables, columns, indexes, foreign keys)
- Full relationship traversal across all 7 core domain models
- Unique constraints enforcement
- Alembic head migration verification
"""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal
from app.models import (
    Application,
    ApplicationStageHistory,
    ApplicationStatus,
    ComplianceRecord,
    ComplianceStatus,
    Document,
    Institution,
    User,
    UserRole,
    WorkflowStage,
)


@pytest.fixture(scope="module")
def db_session():
    """Yield a database session for test execution."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_models_importable_and_registered():
    """All 7 core domain models are registered in Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "institutions",
        "users",
        "applications",
        "workflow_stages",
        "application_stage_histories",
        "compliance_records",
        "documents",
    }
    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"


def test_database_schema_integrity():
    """Verify tables, foreign keys, and unique indexes directly from PostgreSQL."""
    settings = get_settings()
    engine = create_engine(settings.database_url, echo=False)
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())

    expected_tables = [
        "institutions",
        "users",
        "applications",
        "workflow_stages",
        "application_stage_histories",
        "compliance_records",
        "documents",
    ]
    for table in expected_tables:
        assert table in db_tables, f"Table {table} not found in database"

    # Verify unique indexes
    inst_indexes = inspector.get_indexes("institutions")
    assert any(idx["column_names"] == ["institution_code"] and idx["unique"] for idx in inst_indexes)

    user_indexes = inspector.get_indexes("users")
    assert any(idx["column_names"] == ["email"] and idx["unique"] for idx in user_indexes)

    app_indexes = inspector.get_indexes("applications")
    assert any(idx["column_names"] == ["application_number"] and idx["unique"] for idx in app_indexes)

    stage_indexes = inspector.get_indexes("workflow_stages")
    assert any(idx["column_names"] == ["stage_code"] and idx["unique"] for idx in stage_indexes)

    # Verify foreign keys
    doc_fks = inspector.get_foreign_keys("documents")
    referred_tables = {fk["referred_table"] for fk in doc_fks}
    assert {"institutions", "applications", "compliance_records", "users"}.issubset(referred_tables)


def test_full_domain_relationships_lifecycle(db_session: Session):
    """
    Test creating instances of all 7 models in PostgreSQL and navigating
    relationships bidirectionally.
    """
    suffix = uuid.uuid4().hex[:8]

    # 1. Create Institution
    inst = Institution(
        institution_name=f"Govt Polytechnic {suffix}",
        institution_code=f"GP-{suffix}",
        institution_type="Engineering",
        state="Maharashtra",
        district="Pune",
    )
    db_session.add(inst)
    db_session.flush()

    # 2. Create User linked to Institution
    user = User(
        full_name=f"Dr. Officer {suffix}",
        email=f"officer_{suffix}@aicte.gov.in",
        role=UserRole.AICTE_OFFICIAL,
        institution_id=inst.id,
    )
    db_session.add(user)
    db_session.flush()

    # 3. Create Application
    app = Application(
        application_number=f"APP-2026-{suffix}",
        institution_id=inst.id,
        application_type="Extension of Approval",
        academic_year="2026-2027",
        status=ApplicationStatus.SUBMITTED,
        current_stage="Scrutiny",
        submitted_at=datetime.now(timezone.utc),
    )
    db_session.add(app)
    db_session.flush()

    # 4. Create WorkflowStage
    stage = WorkflowStage(
        stage_name=f"Scrutiny {suffix}",
        stage_code=f"SCRUTINY_{suffix}",
        description="Statutory document scrutiny stage",
        sequence_order=1,
    )
    db_session.add(stage)
    db_session.flush()

    # 5. Create ApplicationStageHistory
    history = ApplicationStageHistory(
        application_id=app.id,
        workflow_stage_id=stage.id,
        status="IN_PROGRESS",
        remarks="Scrutiny commenced by regional committee",
        acted_by_user_id=user.id,
    )
    db_session.add(history)
    db_session.flush()

    # 6. Create ComplianceRecord
    compliance = ComplianceRecord(
        institution_id=inst.id,
        application_id=app.id,
        compliance_type="LAND_LEASE",
        title="Land Lease Deed Renewal",
        status=ComplianceStatus.PENDING,
        verified_by_user_id=user.id,
    )
    db_session.add(compliance)
    db_session.flush()

    # 7. Create Document
    doc = Document(
        institution_id=inst.id,
        application_id=app.id,
        compliance_record_id=compliance.id,
        document_name="registered_lease_2026.pdf",
        document_type="LEASE_DOCUMENT",
        storage_key=f"institutions/{inst.id}/docs/{suffix}.pdf",
        mime_type="application/pdf",
        file_size=2048500,
        uploaded_by_user_id=user.id,
    )
    db_session.add(doc)
    db_session.commit()

    # Refresh and test relationship navigations
    db_session.refresh(inst)
    db_session.refresh(app)
    db_session.refresh(user)
    db_session.refresh(stage)
    db_session.refresh(compliance)
    db_session.refresh(doc)

    # Institution -> Users & Applications
    assert any(u.id == user.id for u in inst.users)
    assert any(a.id == app.id for a in inst.applications)
    assert any(c.id == compliance.id for c in inst.compliance_records)
    assert any(d.id == doc.id for d in inst.documents)

    # Application -> Institution, StageHistories, Documents
    assert app.institution.id == inst.id
    assert len(app.stage_histories) >= 1
    assert app.stage_histories[0].workflow_stage.stage_code == stage.stage_code

    # ComplianceRecord -> Documents & VerifiedUser
    assert compliance.verified_by_user.id == user.id
    assert any(d.id == doc.id for d in compliance.documents)

    # Document -> UploadedUser & Compliance
    assert doc.uploaded_by_user.id == user.id
    assert doc.compliance_record.id == compliance.id


def test_unique_constraints_enforced(db_session: Session):
    """Ensure duplicate institution code and duplicate application number violate unique constraints."""
    suffix = uuid.uuid4().hex[:8]

    inst1 = Institution(
        institution_name="Original Institute",
        institution_code=f"UNIQUE-CODE-{suffix}",
    )
    db_session.add(inst1)
    db_session.commit()

    inst2 = Institution(
        institution_name="Duplicate Institute",
        institution_code=f"UNIQUE-CODE-{suffix}",
    )
    db_session.add(inst2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_alembic_database_at_head():
    """Verify that Alembic reports the database migration is at HEAD."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext

    settings = get_settings()
    engine = create_engine(settings.database_url, echo=False)

    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    head_rev = script.get_current_head()

    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()

    assert current_rev is not None, "Database has not had migrations applied."
    assert current_rev == head_rev, f"Database rev ({current_rev}) != Head rev ({head_rev})"
