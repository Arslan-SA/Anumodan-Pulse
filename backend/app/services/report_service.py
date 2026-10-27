"""
AICTE FlowOps — Report Generation Service

Produces structured tabular datasets and downloadable CSV exports for
Application Summaries, Compliance Audits, Overdue Tracking, and Document Expirations.
Enforces institutional isolation and role permissions across all exports.
"""

import csv
from datetime import date, datetime, timedelta, timezone
import io
from typing import Any, List, Literal, Optional, Tuple
import uuid


def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

from fastapi import HTTPException, status
from sqlalchemy import Date, and_, cast, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application
from app.models.compliance import ComplianceRecord
from app.models.document import Document
from app.models.enums import ApplicationStatus, ComplianceStatus, UserRole
from app.models.user import User
from app.schemas.report import (
    ApplicationReportRow,
    ComplianceReportRow,
    DocumentReportRow,
    OverdueReportRow,
)
from app.services.dashboard_service import DashboardService


class ReportService:
    """Service generating downloadable reports and structured datasets."""

    @staticmethod
    def generate_applications_report(
        db: Session,
        user: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status_filter: Optional[ApplicationStatus] = None,
        workflow_stage: Optional[str] = None,
        institution_id: Optional[uuid.UUID] = None,
        report_format: Literal["json", "csv"] = "json",
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[ApplicationReportRow], int, Optional[str], Optional[str]]:
        """
        Generates Application Summary report in JSON rows or CSV text.
        Returns: (rows, total_count, csv_content, csv_filename)
        """
        scoped_inst_id = DashboardService.check_institution_access(user, institution_id)

        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be later than end_date.",
            )

        query = select(Application).options(joinedload(Application.institution))
        count_query = select(func.count(Application.id))

        filters = []
        if scoped_inst_id:
            filters.append(Application.institution_id == scoped_inst_id)
        if status_filter:
            filters.append(Application.status == status_filter)
        if workflow_stage:
            filters.append(Application.current_stage == workflow_stage.strip())
        if start_date:
            filters.append(cast(Application.created_at, Date) >= start_date)
        if end_date:
            filters.append(cast(Application.created_at, Date) <= end_date)

        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        total_count = db.scalar(count_query) or 0

        now = datetime.now()
        if report_format == "csv":
            # Stream all matching records for CSV export (capped at 5000 rows for safety)
            apps = db.scalars(query.order_by(desc(Application.created_at)).limit(5000)).all()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Application Number",
                "Institution Code",
                "Institution Name",
                "Application Type",
                "Academic Year",
                "Status",
                "Current Stage",
                "Submission Date",
                "Days Pending",
                "Created Date",
            ])
            for a in apps:
                ref_time = a.submitted_at or a.created_at
                days_pending = max(0, (now.date() - ref_time.date()).days) if ref_time else 0
                writer.writerow([
                    a.application_number,
                    a.institution.institution_code if a.institution else "N/A",
                    a.institution.institution_name if a.institution else "N/A",
                    a.application_type,
                    a.academic_year,
                    a.status.value if hasattr(a.status, "value") else str(a.status),
                    a.current_stage or "Unassigned",
                    a.submitted_at.strftime("%Y-%m-%d %H:%M") if a.submitted_at else "Not Submitted",
                    days_pending,
                    a.created_at.strftime("%Y-%m-%d %H:%M"),
                ])
            today_str = date.today().isoformat()
            return [], total_count, output.getvalue(), f"applications_report_{today_str}.csv"

        # Paginated JSON
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        apps = (
            db.scalars(
                query.order_by(desc(Application.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .all()
        )

        rows = []
        for a in apps:
            ref_time = a.submitted_at or a.created_at
            days_pending = max(0, (now.date() - ref_time.date()).days) if ref_time else 0
            rows.append(
                ApplicationReportRow(
                    id=a.id,
                    application_number=a.application_number,
                    institution_id=a.institution_id,
                    institution_code=a.institution.institution_code if a.institution else None,
                    institution_name=a.institution.institution_name if a.institution else None,
                    application_type=a.application_type,
                    academic_year=a.academic_year,
                    status=a.status.value if hasattr(a.status, "value") else str(a.status),
                    current_stage=a.current_stage,
                    submitted_at=a.submitted_at,
                    days_pending=days_pending,
                    created_at=a.created_at,
                )
            )

        return rows, total_count, None, None

    @staticmethod
    def generate_compliance_report(
        db: Session,
        user: User,
        status_filter: Optional[ComplianceStatus] = None,
        compliance_type: Optional[str] = None,
        institution_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        report_format: Literal["json", "csv"] = "json",
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[ComplianceReportRow], int, Optional[str], Optional[str]]:
        """
        Generates Compliance Audit report in JSON rows or CSV text.
        """
        scoped_inst_id = DashboardService.check_institution_access(user, institution_id)

        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be later than end_date.",
            )

        query = select(ComplianceRecord).options(
            joinedload(ComplianceRecord.institution),
            joinedload(ComplianceRecord.application),
        )
        count_query = select(func.count(ComplianceRecord.id))

        filters = []
        if scoped_inst_id:
            filters.append(ComplianceRecord.institution_id == scoped_inst_id)
        if status_filter:
            filters.append(ComplianceRecord.status == status_filter)
        if compliance_type:
            filters.append(ComplianceRecord.compliance_type.ilike(f"%{compliance_type.strip()}%"))
        if start_date:
            filters.append(cast(ComplianceRecord.created_at, Date) >= start_date)
        if end_date:
            filters.append(cast(ComplianceRecord.created_at, Date) <= end_date)

        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        total_count = db.scalar(count_query) or 0
        today = date.today()

        if report_format == "csv":
            records = db.scalars(query.order_by(desc(ComplianceRecord.created_at)).limit(5000)).all()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Compliance ID",
                "Institution Name",
                "Application Number",
                "Compliance Type",
                "Title",
                "Status",
                "Due Date",
                "Submitted At",
                "Verified At",
                "Overdue",
            ])
            for c in records:
                is_overdue = (
                    c.status == ComplianceStatus.OVERDUE
                    or (c.due_date and c.due_date < today and c.status in [
                        ComplianceStatus.PENDING,
                        ComplianceStatus.SUBMITTED,
                        ComplianceStatus.REJECTED,
                    ])
                )
                writer.writerow([
                    str(c.id),
                    c.institution.institution_name if c.institution else "N/A",
                    c.application.application_number if c.application else "N/A",
                    c.compliance_type,
                    c.title,
                    c.status.value if hasattr(c.status, "value") else str(c.status),
                    c.due_date.isoformat() if c.due_date else "No Due Date",
                    c.submitted_at.strftime("%Y-%m-%d %H:%M") if c.submitted_at else "Not Submitted",
                    c.verified_at.strftime("%Y-%m-%d %H:%M") if c.verified_at else "Unverified",
                    "YES" if is_overdue else "NO",
                ])
            today_str = date.today().isoformat()
            return [], total_count, output.getvalue(), f"compliance_report_{today_str}.csv"

        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        records = (
            db.scalars(
                query.order_by(desc(ComplianceRecord.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .all()
        )

        rows = []
        for c in records:
            is_overdue = bool(
                c.status == ComplianceStatus.OVERDUE
                or (c.due_date and c.due_date < today and c.status in [
                    ComplianceStatus.PENDING,
                    ComplianceStatus.SUBMITTED,
                    ComplianceStatus.REJECTED,
                ])
            )
            rows.append(
                ComplianceReportRow(
                    id=c.id,
                    institution_id=c.institution_id,
                    institution_name=c.institution.institution_name if c.institution else None,
                    application_id=c.application_id,
                    application_number=c.application.application_number if c.application else None,
                    compliance_type=c.compliance_type,
                    title=c.title,
                    status=c.status.value if hasattr(c.status, "value") else str(c.status),
                    due_date=c.due_date,
                    submitted_at=c.submitted_at,
                    verified_at=c.verified_at,
                    is_overdue=is_overdue,
                )
            )

        return rows, total_count, None, None

    @staticmethod
    def generate_overdue_report(
        db: Session,
        user: User,
        institution_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        report_format: Literal["json", "csv"] = "json",
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[OverdueReportRow], int, Optional[str], Optional[str]]:
        """
        Generates combined overdue report tracking overdue compliance undertakings
        and ageing applications exceeding 30-day pending threshold.
        """
        scoped_inst_id = DashboardService.check_institution_access(user, institution_id)
        today = date.today()
        now = datetime.now()
        overdue_rows: List[OverdueReportRow] = []

        # 1. Overdue Compliance Items
        if entity_type in [None, "", "compliance"]:
            comp_filters = [
                or_(
                    ComplianceRecord.status == ComplianceStatus.OVERDUE,
                    and_(
                        ComplianceRecord.due_date < today,
                        ComplianceRecord.status.in_([
                            ComplianceStatus.PENDING,
                            ComplianceStatus.SUBMITTED,
                            ComplianceStatus.REJECTED,
                        ]),
                    ),
                )
            ]
            if scoped_inst_id:
                comp_filters.append(ComplianceRecord.institution_id == scoped_inst_id)

            comp_records = (
                db.scalars(
                    select(ComplianceRecord)
                    .options(joinedload(ComplianceRecord.institution))
                    .where(*comp_filters)
                    .order_by(ComplianceRecord.due_date)
                    .limit(500)
                )
                .all()
            )

            for c in comp_records:
                days_overdue = (today - c.due_date).days if c.due_date else 0
                overdue_rows.append(
                    OverdueReportRow(
                        entity_type="compliance",
                        entity_id=c.id,
                        reference_number=c.title,
                        institution_name=c.institution.institution_name if c.institution else None,
                        current_status=c.status.value if hasattr(c.status, "value") else str(c.status),
                        target_date=c.due_date.isoformat() if c.due_date else None,
                        days_overdue=max(0, days_overdue),
                        remarks=f"Compliance type: {c.compliance_type}",
                    )
                )

        # 2. Ageing Applications (> 30 days pending)
        if entity_type in [None, "", "application"]:
            app_filters = [
                Application.submitted_at.isnot(None),
                Application.status.in_([
                    ApplicationStatus.SUBMITTED,
                    ApplicationStatus.UNDER_SCRUTINY,
                    ApplicationStatus.RETURNED_FOR_CLARIFICATION,
                    ApplicationStatus.EVC_PENDING,
                    ApplicationStatus.EVC_SCHEDULED,
                    ApplicationStatus.UNDER_REVIEW,
                ]),
                Application.submitted_at <= now - timedelta(days=30),
            ]
            if scoped_inst_id:
                app_filters.append(Application.institution_id == scoped_inst_id)

            ageing_apps = (
                db.scalars(
                    select(Application)
                    .options(joinedload(Application.institution))
                    .where(*app_filters)
                    .order_by(Application.submitted_at)
                    .limit(500)
                )
                .all()
            )

            for a in ageing_apps:
                days_pending = (now.date() - a.submitted_at.date()).days if a.submitted_at else 0
                overdue_rows.append(
                    OverdueReportRow(
                        entity_type="application",
                        entity_id=a.id,
                        reference_number=a.application_number,
                        institution_name=a.institution.institution_name if a.institution else None,
                        current_status=a.status.value if hasattr(a.status, "value") else str(a.status),
                        target_date=a.submitted_at.date().isoformat() if a.submitted_at else None,
                        days_overdue=days_pending,
                        remarks=f"Stage: {a.current_stage or 'Unassigned'}",
                    )
                )

        # Sort combined results by days_overdue descending
        overdue_rows.sort(key=lambda x: x.days_overdue, reverse=True)
        total_count = len(overdue_rows)

        if report_format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Entity Type",
                "Reference Number / Title",
                "Institution Name",
                "Current Status",
                "Target / Submission Date",
                "Days Overdue / Pending",
                "Remarks",
            ])
            for r in overdue_rows:
                writer.writerow([
                    r.entity_type.upper(),
                    r.reference_number,
                    r.institution_name or "N/A",
                    r.current_status,
                    r.target_date or "N/A",
                    r.days_overdue,
                    r.remarks or "",
                ])
            today_str = date.today().isoformat()
            return [], total_count, output.getvalue(), f"overdue_report_{today_str}.csv"

        # Paginated JSON
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        start_idx = (page - 1) * page_size
        paginated_rows = overdue_rows[start_idx : start_idx + page_size]

        return paginated_rows, total_count, None, None

    @staticmethod
    def generate_documents_report(
        db: Session,
        user: User,
        institution_id: Optional[uuid.UUID] = None,
        days_window: Optional[int] = 30,
        document_type: Optional[str] = None,
        report_format: Literal["json", "csv"] = "json",
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[DocumentReportRow], int, Optional[str], Optional[str]]:
        """
        Generates Document Expiry and Metadata report.
        """
        scoped_inst_id = DashboardService.check_institution_access(user, institution_id)

        query = select(Document).options(
            joinedload(Document.institution),
            joinedload(Document.application),
        )
        count_query = select(func.count(Document.id))

        filters = []
        if scoped_inst_id:
            filters.append(Document.institution_id == scoped_inst_id)
        if document_type:
            filters.append(Document.document_type.ilike(f"%{document_type.strip()}%"))

        now = datetime.now(timezone.utc)
        if days_window is not None:
            # Filter documents expiring within N days or already expired
            window_limit = now + timedelta(days=days_window)
            filters.append(
                or_(
                    Document.expires_at < now,
                    and_(Document.expires_at >= now, Document.expires_at <= window_limit),
                )
            )

        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        total_count = db.scalar(count_query) or 0

        if report_format == "csv":
            docs = db.scalars(query.order_by(Document.expires_at).limit(5000)).all()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Document Name",
                "Document Type",
                "Institution Name",
                "Application Number",
                "Mime Type",
                "File Size (KB)",
                "Uploaded At",
                "Expires At",
                "Status",
            ])
            for d in docs:
                d_exp = _normalize_dt(d.expires_at)
                if not d_exp:
                    status_str = "VALID (NO EXPIRY)"
                elif d_exp < now:
                    status_str = "EXPIRED"
                elif d_exp <= now + timedelta(days=30):
                    status_str = "EXPIRING SOON"
                else:
                    status_str = "VALID"

                file_size_kb = round(d.file_size / 1024, 1) if d.file_size else 0
                writer.writerow([
                    d.document_name,
                    d.document_type,
                    d.institution.institution_name if d.institution else "N/A",
                    d.application.application_number if d.application else "N/A",
                    d.mime_type or "Unknown",
                    file_size_kb,
                    d.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                    d.expires_at.strftime("%Y-%m-%d %H:%M") if d.expires_at else "None",
                    status_str,
                ])
            today_str = date.today().isoformat()
            return [], total_count, output.getvalue(), f"documents_report_{today_str}.csv"

        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        docs = (
            db.scalars(
                query.order_by(Document.expires_at)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .all()
        )

        rows = []
        for d in docs:
            d_exp = _normalize_dt(d.expires_at)
            if not d_exp:
                status_str = "NO_EXPIRY"
            elif d_exp < now:
                status_str = "EXPIRED"
            elif d_exp <= now + timedelta(days=30):
                status_str = "EXPIRING_SOON"
            else:
                status_str = "VALID"

            rows.append(
                DocumentReportRow(
                    id=d.id,
                    document_name=d.document_name,
                    document_type=d.document_type,
                    institution_id=d.institution_id,
                    institution_name=d.institution.institution_name if d.institution else None,
                    application_id=d.application_id,
                    application_number=d.application.application_number if d.application else None,
                    mime_type=d.mime_type,
                    file_size=d.file_size,
                    uploaded_at=d.uploaded_at,
                    expires_at=d.expires_at,
                    expiry_status=status_str,
                )
            )

        return rows, total_count, None, None
