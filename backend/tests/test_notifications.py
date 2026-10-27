"""
AICTE FlowOps — Notifications, Reminders, Alerts & Escalations Tests (Phase 7)

Validates:
- Notification created for correct recipient
- User sees only own notifications (strict privacy)
- Mark notification as read
- Mark all notifications as read
- Archive notification
- Unread count tally
- Duplicate notification prevention (dedup_key)
- Deadline monitoring: compliance due soon
- Deadline monitoring: compliance overdue
- Deadline monitoring: document expiring
- Deadline monitoring: document expired
- Deadline monitoring: application pending beyond threshold
- No alert when no deadline or threshold is configured
- No repeated duplicate alert for the same event
- Configured escalation is created and history preserved
- Unauthorized user cannot configure reminder rules
- Escalation does not change application approval status
- Scheduler does not run during tests, job can be triggered manually and retried safely
"""

from datetime import date, datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from sqlalchemy import select
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
from app.models.reminder_rule import ReminderRule
from app.models.user import User
from app.services.deadline_service import DeadlineService
from app.services.notification_service import NotificationService
from app.services.scheduler import _scheduler, run_deadline_check_job
from app.utils.security import create_access_token, hash_password


@pytest.fixture
def institution_alpha():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Alpha University {suffix}",
            institution_code=f"ALU-{suffix}",
            institution_type="University",
            state="Delhi",
            district="South Delhi",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def institution_beta():
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        inst = Institution(
            institution_name=f"Beta Technical Institute {suffix}",
            institution_code=f"BTI-{suffix}",
            institution_type="Engineering",
            state="Karnataka",
            district="Bengaluru",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst


@pytest.fixture
def user_alpha(institution_alpha):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Dean Alpha {suffix}",
            email=f"alpha_dean_{suffix}@alpha.edu",
            hashed_password=hash_password("Pass123!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_alpha.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture
def user_beta(institution_beta):
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        user = User(
            full_name=f"Dean Beta {suffix}",
            email=f"beta_dean_{suffix}@beta.edu",
            hashed_password=hash_password("Pass123!"),
            role=UserRole.INSTITUTION_USER,
            institution_id=institution_beta.id,
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


class TestNotificationLifecycle:

    def test_notification_created_for_correct_recipient(self, client: TestClient, user_alpha):
        """Notification service delivers alert to target user with correct fields."""
        with SessionLocal() as db:
            notif = NotificationService.send_notification(
                db=db,
                recipient_user_id=user_alpha.id,
                notification_type=NotificationType.APPLICATION_STAGE_UPDATED,
                title="Stage Transition",
                message="Your application moved to Scrutiny Committee Review.",
                priority=NotificationPriority.MEDIUM,
            )
            assert notif is not None
            assert notif.recipient_user_id == user_alpha.id
            assert notif.status == NotificationStatus.UNREAD
            assert notif.read_at is None

        # Verify API query returns notification
        res = client.get("/api/v1/notifications", headers=auth_header(user_alpha))
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) >= 1
        assert items[0]["title"] == "Stage Transition"

    def test_user_sees_only_own_notifications(self, client: TestClient, user_alpha, user_beta, admin_user):
        """Users and admins can only view their own notifications."""
        with SessionLocal() as db:
            NotificationService.send_notification(
                db=db,
                recipient_user_id=user_beta.id,
                notification_type=NotificationType.COMPLIANCE_REJECTED,
                title="Private Beta Undertaking Alert",
                message="Secret details for Beta only.",
            )

        # Alpha user lists notifications: Beta's alert must not appear
        res_alpha = client.get("/api/v1/notifications", headers=auth_header(user_alpha))
        assert res_alpha.status_code == 200
        titles_alpha = [n["title"] for n in res_alpha.json()["items"]]
        assert "Private Beta Undertaking Alert" not in titles_alpha

        # Admin also sees only own notifications, not other users'
        res_admin = client.get("/api/v1/notifications", headers=auth_header(admin_user))
        assert res_admin.status_code == 200
        titles_admin = [n["title"] for n in res_admin.json()["items"]]
        assert "Private Beta Undertaking Alert" not in titles_admin

    def test_mark_notification_as_read(self, client: TestClient, user_alpha):
        """User can mark their notification as read, recording UTC read_at."""
        with SessionLocal() as db:
            notif = NotificationService.send_notification(
                db=db,
                recipient_user_id=user_alpha.id,
                notification_type=NotificationType.APPLICATION_SUBMITTED,
                title="Submission Ack",
                message="Submission registered.",
            )
            notif_id = str(notif.id)

        res = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=auth_header(user_alpha))
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == NotificationStatus.READ.value
        assert data["read_at"] is not None

    def test_mark_all_notifications_as_read(self, client: TestClient, user_alpha):
        """Bulk read updates all unread notifications for the user."""
        with SessionLocal() as db:
            for i in range(3):
                NotificationService.send_notification(
                    db=db,
                    recipient_user_id=user_alpha.id,
                    notification_type=NotificationType.APPLICATION_STAGE_UPDATED,
                    title=f"Update {i}",
                    message="Stage progressed.",
                )

        res = client.post("/api/v1/notifications/mark-all-read", headers=auth_header(user_alpha))
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert res.json()["updated_count"] >= 3

        # Unread count should now be 0
        count_res = client.get("/api/v1/notifications/unread-count", headers=auth_header(user_alpha))
        assert count_res.status_code == 200
        assert count_res.json()["unread_count"] == 0

    def test_archive_notification(self, client: TestClient, user_alpha):
        """User can archive a notification."""
        with SessionLocal() as db:
            notif = NotificationService.send_notification(
                db=db,
                recipient_user_id=user_alpha.id,
                notification_type=NotificationType.APPLICATION_STAGE_UPDATED,
                title="Archivable Item",
                message="Old event.",
            )
            notif_id = str(notif.id)

        res = client.patch(f"/api/v1/notifications/{notif_id}/archive", headers=auth_header(user_alpha))
        assert res.status_code == 200
        assert res.json()["status"] == NotificationStatus.ARCHIVED.value

    def test_unread_count_endpoint(self, client: TestClient, user_alpha):
        """Unread count matches active unread records."""
        with SessionLocal() as db:
            NotificationService.send_notification(
                db=db,
                recipient_user_id=user_alpha.id,
                notification_type=NotificationType.EVC_SCHEDULED,
                title="EVC Committee Visit",
                message="Physical visit scheduled.",
            )

        res = client.get("/api/v1/notifications/unread-count", headers=auth_header(user_alpha))
        assert res.status_code == 200
        assert res.json()["unread_count"] >= 1

    def test_duplicate_notification_prevention(self, user_alpha):
        """Deduplication key prevents duplicate notifications for the same event."""
        with SessionLocal() as db:
            dedup = f"TEST_DEDUP:{uuid.uuid4().hex}"
            n1 = NotificationService.send_notification(
                db=db,
                recipient_user_id=user_alpha.id,
                notification_type=NotificationType.COMPLIANCE_DUE_SOON,
                title="Reminder",
                message="First reminder.",
                dedup_key=dedup,
            )
            assert n1 is not None

            # Second send with same dedup_key must return None and not insert
            n2 = NotificationService.send_notification(
                db=db,
                recipient_user_id=user_alpha.id,
                notification_type=NotificationType.COMPLIANCE_DUE_SOON,
                title="Reminder",
                message="Duplicate reminder attempt.",
                dedup_key=dedup,
            )
            assert n2 is None


class TestDeadlineMonitoringAndAlerts:

    def test_compliance_due_soon_alert(self, user_alpha, institution_alpha):
        """Pending compliance due within configured window triggers due-soon notification."""
        with SessionLocal() as db:
            rec = ComplianceRecord(
                institution_id=institution_alpha.id,
                compliance_type="Fire Safety",
                title="Fire Safety Certificate 2026",
                due_date=date.today() + timedelta(days=3),  # 3 days window
                status=ComplianceStatus.PENDING,
            )
            db.add(rec)
            db.commit()
            db.refresh(rec)

            stats = DeadlineService.evaluate_deadlines_and_reminders(db)
            assert stats["compliance_due_soon"] >= 1

            # Check that user_alpha received the notification
            notifs = list(
                db.scalars(
                    select(Notification).where(
                        Notification.recipient_user_id == user_alpha.id,
                        Notification.notification_type == NotificationType.COMPLIANCE_DUE_SOON,
                    )
                ).all()
            )
            assert len(notifs) >= 1
            assert "3 Days" in notifs[0].title

    def test_compliance_overdue_and_escalation(self, user_alpha, institution_alpha, official_user):
        """Overdue compliance triggers overdue notification and supervisory escalation."""
        with SessionLocal() as db:
            rec = ComplianceRecord(
                institution_id=institution_alpha.id,
                compliance_type="Faculty Roster",
                title="Overdue Faculty Qualifications",
                due_date=date.today() - timedelta(days=10),  # 10 days overdue
                status=ComplianceStatus.PENDING,
            )
            db.add(rec)
            db.commit()
            db.refresh(rec)

            stats = DeadlineService.evaluate_deadlines_and_reminders(db)
            assert stats["compliance_overdue"] >= 1
            assert stats["compliance_escalations"] >= 1

            # Institution user received COMPLIANCE_OVERDUE
            inst_notifs = list(
                db.scalars(
                    select(Notification).where(
                        Notification.recipient_user_id == user_alpha.id,
                        Notification.notification_type == NotificationType.COMPLIANCE_OVERDUE,
                    )
                ).all()
            )
            assert len(inst_notifs) >= 1

            # Official user received ESCALATION
            off_notifs = list(
                db.scalars(
                    select(Notification).where(
                        Notification.recipient_user_id == official_user.id,
                        Notification.notification_type == NotificationType.ESCALATION,
                    )
                ).all()
            )
            assert len(off_notifs) >= 1

    def test_document_expiring_and_expired(self, user_alpha, institution_alpha):
        """Expiring and expired documents generate appropriate alert notifications."""
        with SessionLocal() as db:
            # 1. Document expiring in 7 days
            doc_soon = Document(
                institution_id=institution_alpha.id,
                document_name="Building Plan 2026",
                document_type="Safety NOC",
                storage_key="test/soon.pdf",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
            # 2. Document expired 2 days ago
            doc_past = Document(
                institution_id=institution_alpha.id,
                document_name="Old Water Certificate",
                document_type="Health NOC",
                storage_key="test/past.pdf",
                expires_at=datetime.now(timezone.utc) - timedelta(days=2),
            )
            db.add_all([doc_soon, doc_past])
            db.commit()

            stats = DeadlineService.evaluate_deadlines_and_reminders(db)
            assert stats["documents_expiring"] >= 1
            assert stats["documents_expired"] >= 1

    def test_no_alert_when_no_deadline_configured(self, user_alpha, institution_alpha):
        """Compliance or documents without due dates/expiry dates produce no alerts."""
        with SessionLocal() as db:
            rec_no_date = ComplianceRecord(
                institution_id=institution_alpha.id,
                compliance_type="General",
                title="Undated Compliance",
                due_date=None,
                status=ComplianceStatus.PENDING,
            )
            doc_no_exp = Document(
                institution_id=institution_alpha.id,
                document_name="Permanent Deed",
                document_type="Title",
                storage_key="test/perm.pdf",
                expires_at=None,
            )
            db.add_all([rec_no_date, doc_no_exp])
            db.commit()

            # Evaluating deadlines should produce 0 alerts for these items
            stats = DeadlineService.evaluate_deadlines_and_reminders(db)
            # Checking no notification with "Undated Compliance" title
            found = db.scalar(
                select(Notification.id).where(Notification.title.ilike("%Undated Compliance%"))
            )
            assert found is None

    def test_no_repeated_duplicate_alerts_on_consecutive_runs(self, user_alpha, institution_alpha):
        """Consecutive scheduler evaluations do not send duplicate notifications for the same event."""
        with SessionLocal() as db:
            rec = ComplianceRecord(
                institution_id=institution_alpha.id,
                compliance_type="Electrical Safety",
                title="Electrical NOC",
                due_date=date.today() + timedelta(days=1),  # 1 day window
                status=ComplianceStatus.PENDING,
            )
            db.add(rec)
            db.commit()

            # First run: creates notification
            stats1 = DeadlineService.evaluate_deadlines_and_reminders(db)
            assert stats1["compliance_due_soon"] >= 1

            # Second immediate run: dedup keys prevent duplicate notifications
            stats2 = DeadlineService.evaluate_deadlines_and_reminders(db)
            assert stats2["compliance_due_soon"] == 0


class TestEscalationAndReminderRules:

    def test_escalation_history_preserved_without_altering_status(self, admin_user, institution_alpha):
        """Escalation records history and leaves application status strictly intact."""
        with SessionLocal() as db:
            # Create application pending for 20 days
            old_time = datetime.now(timezone.utc) - timedelta(days=20)
            app = Application(
                application_number=f"APP-ESC-{uuid.uuid4().hex[:4]}",
                institution_id=institution_alpha.id,
                application_type="New Course",
                academic_year="2026-2027",
                status=ApplicationStatus.UNDER_SCRUTINY,
                submitted_at=old_time,
                created_at=old_time,
            )
            db.add(app)
            db.commit()
            db.refresh(app)

            original_status = app.status

            # Trigger deadline check
            DeadlineService.evaluate_deadlines_and_reminders(db)

            # Re-read application: status MUST remain unchanged
            db.refresh(app)
            assert app.status == original_status

            # EscalationHistory record exists
            esc = db.scalar(
                select(EscalationHistory).where(
                    EscalationHistory.entity_id == app.id,
                    EscalationHistory.entity_type == "Application",
                )
            )
            assert esc is not None
            assert "Inactivity" in esc.rule_name

    def test_unauthorized_user_cannot_configure_reminder_rules(self, client: TestClient, user_alpha, official_user):
        """Only system admins can configure reminder rules."""
        payload = {
            "name": "Custom 10-Day Pre-Deadline Rule",
            "event_type": "COMPLIANCE_DUE_SOON",
            "days_before_deadline": 10,
        }

        # Institution user forbidden (403)
        res_inst = client.post("/api/v1/reminder-rules", json=payload, headers=auth_header(user_alpha))
        assert res_inst.status_code == 403

        # Official forbidden (Admin only, 403)
        res_off = client.post("/api/v1/reminder-rules", json=payload, headers=auth_header(official_user))
        assert res_off.status_code == 403

    def test_admin_configures_reminder_rule(self, client: TestClient, admin_user):
        """Admin successfully creates, updates, and toggles reminder rule."""
        payload = {
            "name": f"Rule {uuid.uuid4().hex[:6]}",
            "event_type": "COMPLIANCE_DUE_SOON",
            "days_before_deadline": 21,
            "priority": NotificationPriority.HIGH.value,
        }
        create_res = client.post("/api/v1/reminder-rules", json=payload, headers=auth_header(admin_user))
        assert create_res.status_code == 201
        rule_id = create_res.json()["id"]

        # Update
        patch_res = client.patch(
            f"/api/v1/reminder-rules/{rule_id}",
            json={"priority": NotificationPriority.CRITICAL.value},
            headers=auth_header(admin_user),
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["priority"] == NotificationPriority.CRITICAL.value

        # Toggle status
        toggle_res = client.patch(
            f"/api/v1/reminder-rules/{rule_id}/status",
            json={"is_active": False},
            headers=auth_header(admin_user),
        )
        assert toggle_res.status_code == 200
        assert toggle_res.json()["is_active"] is False


class TestBackgroundScheduler:

    def test_scheduler_does_not_run_during_tests(self):
        """Verify scheduler background loop is disabled in test environment."""
        assert settings.enable_scheduler is False
        assert _scheduler is None or not _scheduler.running

    def test_job_can_be_triggered_manually_and_safely_retried(self):
        """run_deadline_check_job can be safely invoked and retried without crashing."""
        stats1 = run_deadline_check_job()
        assert isinstance(stats1, dict)
        assert "error" not in stats1

        # Immediate retry executes without failure
        stats2 = run_deadline_check_job()
        assert isinstance(stats2, dict)
        assert "error" not in stats2
