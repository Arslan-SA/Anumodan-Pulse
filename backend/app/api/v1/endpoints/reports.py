"""
AICTE FlowOps — Reporting Endpoints

Exports and tabulations for Applications, Compliance Records,
Overdue Deadlines, and Document Metadata with JSON and CSV downloads.
"""

from datetime import date
import math
from typing import Literal, Optional
import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.enums import ApplicationStatus, ComplianceStatus
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.report import (
    ApplicationReportRow,
    ComplianceReportRow,
    DocumentReportRow,
    OverdueReportRow,
)
from app.services.report_service import ReportService

router = APIRouter()


@router.get(
    "/applications",
    response_model=Optional[PaginatedResponse[ApplicationReportRow]],
    status_code=status.HTTP_200_OK,
    summary="Application summary report",
    description=(
        "Retrieves filtered application report data. "
        "Supports structured JSON (with pagination) and direct CSV download."
    ),
)
def get_applications_report(
    start_date: Optional[date] = Query(None, description="Applications submitted/created on or after date"),
    end_date: Optional[date] = Query(None, description="Applications submitted/created on or before date"),
    status: Optional[ApplicationStatus] = Query(None, description="Filter by status"),
    workflow_stage: Optional[str] = Query(None, description="Filter by workflow stage"),
    institution_id: Optional[uuid.UUID] = Query(None, description="Institution filter (Admin/Official only)"),
    format: Literal["json", "csv"] = Query("json", description="Output format: 'json' or 'csv'"),
    page: int = Query(1, ge=1, description="Page number for JSON output"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page for JSON output"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rows, total, csv_content, filename = ReportService.generate_applications_report(
        db=db,
        user=current_user,
        start_date=start_date,
        end_date=end_date,
        status_filter=status,
        workflow_stage=workflow_stage,
        institution_id=institution_id,
        report_format=format,
        page=page,
        page_size=page_size,
    )
    if format == "csv":
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    return PaginatedResponse[ApplicationReportRow](
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/compliance",
    response_model=Optional[PaginatedResponse[ComplianceReportRow]],
    status_code=status.HTTP_200_OK,
    summary="Compliance status report",
    description=(
        "Retrieves compliance verification audit records and undertaking fulfillment. "
        "Supports structured JSON (with pagination) and direct CSV download."
    ),
)
def get_compliance_report(
    status: Optional[ComplianceStatus] = Query(None, description="Filter by compliance status"),
    compliance_type: Optional[str] = Query(None, description="Filter by compliance type"),
    institution_id: Optional[uuid.UUID] = Query(None, description="Institution filter (Admin/Official only)"),
    start_date: Optional[date] = Query(None, description="Created on or after date"),
    end_date: Optional[date] = Query(None, description="Created on or before date"),
    format: Literal["json", "csv"] = Query("json", description="Output format: 'json' or 'csv'"),
    page: int = Query(1, ge=1, description="Page number for JSON output"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page for JSON output"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rows, total, csv_content, filename = ReportService.generate_compliance_report(
        db=db,
        user=current_user,
        status_filter=status,
        compliance_type=compliance_type,
        institution_id=institution_id,
        start_date=start_date,
        end_date=end_date,
        report_format=format,
        page=page,
        page_size=page_size,
    )
    if format == "csv":
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    return PaginatedResponse[ComplianceReportRow](
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/overdue",
    response_model=Optional[PaginatedResponse[OverdueReportRow]],
    status_code=status.HTTP_200_OK,
    summary="Overdue deadlines and ageing report",
    description=(
        "Retrieves overdue compliance records and ageing applications (>30 days). "
        "Supports structured JSON (with pagination) and direct CSV download."
    ),
)
def get_overdue_report(
    institution_id: Optional[uuid.UUID] = Query(None, description="Institution filter (Admin/Official only)"),
    entity_type: Optional[str] = Query(None, description="Filter entity type: 'application' or 'compliance'"),
    format: Literal["json", "csv"] = Query("json", description="Output format: 'json' or 'csv'"),
    page: int = Query(1, ge=1, description="Page number for JSON output"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page for JSON output"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rows, total, csv_content, filename = ReportService.generate_overdue_report(
        db=db,
        user=current_user,
        institution_id=institution_id,
        entity_type=entity_type,
        report_format=format,
        page=page,
        page_size=page_size,
    )
    if format == "csv":
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    return PaginatedResponse[OverdueReportRow](
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/documents",
    response_model=Optional[PaginatedResponse[DocumentReportRow]],
    status_code=status.HTTP_200_OK,
    summary="Document expiry and validity report",
    description=(
        "Retrieves document metadata and impending expirations within specified days window. "
        "Supports structured JSON (with pagination) and direct CSV download."
    ),
)
def get_documents_report(
    institution_id: Optional[uuid.UUID] = Query(None, description="Institution filter (Admin/Official only)"),
    days_window: Optional[int] = Query(30, description="Window in days to check for expiring documents"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    format: Literal["json", "csv"] = Query("json", description="Output format: 'json' or 'csv'"),
    page: int = Query(1, ge=1, description="Page number for JSON output"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page for JSON output"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rows, total, csv_content, filename = ReportService.generate_documents_report(
        db=db,
        user=current_user,
        institution_id=institution_id,
        days_window=days_window,
        document_type=document_type,
        report_format=format,
        page=page,
        page_size=page_size,
    )
    if format == "csv":
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    return PaginatedResponse[DocumentReportRow](
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
