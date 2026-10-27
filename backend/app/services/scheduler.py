"""
AICTE FlowOps — Background Task Scheduler

Configures APScheduler for periodic deadline checks, reminder notifications,
and overdue escalations.

Features:
- Singleton lifecycle prevention to avoid multiple duplicate schedulers in reload loops
- Isolated database sessions for background jobs
- Non-blocking asynchronous task execution
- Guarded error handling preventing API server interruption
- Bypassed automatically when settings.enable_scheduler is False (e.g. during test suites)
"""

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.database import SessionLocal
from app.services.deadline_service import DeadlineService

logger = logging.getLogger("aicte_flowops.scheduler")

_scheduler: Optional[BackgroundScheduler] = None


def run_deadline_check_job() -> dict:
    """
    Executes a single cycle of statutory deadline, expiry, and escalation checks.
    Can be invoked periodically by APScheduler or triggered manually in unit tests.
    """
    logger.info("Executing periodic statutory deadline monitoring scan...")
    with SessionLocal() as db:
        try:
            stats = DeadlineService.evaluate_deadlines_and_reminders(db)
            logger.info("Statutory deadline scan completed: %s", stats)
            return stats
        except Exception as e:
            logger.exception("Error occurred during deadline monitoring check: %s", str(e))
            return {"error": str(e)}


def start_scheduler() -> Optional[BackgroundScheduler]:
    """
    Initialize and start the background scheduler if enabled in settings.
    Guarantees single instance creation in dev reloaders.
    """
    global _scheduler

    if not settings.enable_scheduler:
        logger.info("Background scheduler is disabled via configuration.")
        return None

    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler is already running; skipping duplicate initialization.")
        return _scheduler

    logger.info(
        "Starting BackgroundScheduler with interval: %d minutes",
        settings.scheduler_interval_minutes,
    )

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        run_deadline_check_job,
        trigger=IntervalTrigger(minutes=settings.scheduler_interval_minutes),
        id="deadline_monitoring_job",
        name="Statutory Deadline and Expiry Monitoring",
        replace_existing=True,
    )
    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    """Gracefully shut down background scheduler on server shutdown."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("Shutting down BackgroundScheduler...")
        _scheduler.shutdown(wait=False)
        _scheduler = None
