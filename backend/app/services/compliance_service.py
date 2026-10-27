"""
AICTE FlowOps — Compliance Service

Encapsulates business and regulatory logic for statutory compliance, undertakings,
verification workflows, and compliance requirements configuration.
"""

from datetime import datetime, timezone
import math
from typing import List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application
from app.models.compliance import ComplianceRecord
from app.models.compliance_history import ComplianceHistory
from app.models.compliance_requirement import ComplianceRequirement
from app.models.document import Document
from app.models.enums import ComplianceStatus, UserRole
from app.models.institution import Institution
from app.models.user import User
from app.schemas.compliance import (
    ComplianceRecordCreate,
    ComplianceRecordUpdate,
)
from app.schemas.compliance_requirement import (
    ComplianceRequirementCreate,
    ComplianceRequirementUpdate,
)


class ComplianceService:

    # ── Compliance Requirements Configuration (Admin-Only) ────────────

    @staticmethod
    def create_requirement(
        db: Session,
        admin_user: User,
        payload: ComplianceRequirementCreate,
    ) -> ComplianceRequirement:
        """Admin creates a new configurable compliance requirement."""
        if admin_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can configure compliance requirements.",
            )

        requirement = ComplianceRequirement(
            name=payload.name.strip(),
            compliance_type=payload.compliance_type.strip(),
            description=payload.description.strip() if payload.description else None,
            application_type=payload.application_type.strip() if payload.application_type else None,
            is_required=payload.is_required,
            allowed_document_types=payload.allowed_document_types,
            default_due_period_days=payload.default_due_period_days,
            is_active=payload.is_active,
        )
        db.add(requirement)
        db.commit()
        db.refresh(requirement)
        return requirement

    @staticmethod
    def list_requirements(
        db: Session,
        active_only: bool = False,
        application_type: Optional[str] = None,
        compliance_type: Optional[str] = None,
    ) -> List[ComplianceRequirement]:
        """List configured compliance requirements."""
        query = select(ComplianceRequirement).order_by(ComplianceRequirement.name.asc())
        if active_only:
            query = query.where(ComplianceRequirement.is_active.is_(True))
        if application_type:
            query = query.where(
                or_(
                    ComplianceRequirement.application_type.is_(None),
                    ComplianceRequirement.application_type == application_type,
                )
            )
        if compliance_type:
            query = query.where(ComplianceRequirement.compliance_type == compliance_type)

        return list(db.scalars(query).all())

    @staticmethod
    def get_requirement(db: Session, requirement_id: uuid.UUID) -> ComplianceRequirement:
        req = db.scalar(select(ComplianceRequirement).where(ComplianceRequirement.id == requirement_id))
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Compliance requirement '{requirement_id}' not found.",
            )
        return req

    @staticmethod
    def update_requirement(
        db: Session,
        admin_user: User,
        requirement_id: uuid.UUID,
        payload: ComplianceRequirementUpdate,
    ) -> ComplianceRequirement:
        """Admin modifies a requirement without rewriting existing records."""
        if admin_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can update compliance requirements.",
            )

        requirement = ComplianceService.get_requirement(db, requirement_id)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(requirement, field, value)

        db.commit()
        db.refresh(requirement)
        return requirement

    @staticmethod
    def update_requirement_status(
        db: Session,
        admin_user: User,
        requirement_id: uuid.UUID,
        is_active: bool,
    ) -> ComplianceRequirement:
        """Admin toggles activation status of a requirement."""
        if admin_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can change compliance requirement status.",
            )

        requirement = ComplianceService.get_requirement(db, requirement_id)
        requirement.is_active = is_active
        db.commit()
        db.refresh(requirement)
        return requirement

    # ── Compliance Records Management ──────────────────────────────────

    @staticmethod
    def create_compliance_record(
        db: Session,
        user: User,
        payload: ComplianceRecordCreate,
    ) -> ComplianceRecord:
        """
        Create a new compliance record.
        Only INSTITUTION_USER can create records, automatically bound to their institution.
        """
        if user.role != UserRole.INSTITUTION_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only institution users can create compliance submissions.",
            )

        if not user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not affiliated with an approved institution.",
            )

        # Validate application ownership if application_id is provided
        target_app: Optional[Application] = None
        if payload.application_id:
            target_app = db.scalar(
                select(Application).where(Application.id == payload.application_id)
            )
            if not target_app or target_app.institution_id != user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Application '{payload.application_id}' not found or belongs to another institution.",
                )

        record = ComplianceRecord(
            institution_id=user.institution_id,
            application_id=payload.application_id,
            compliance_type=payload.compliance_type.strip(),
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            due_date=payload.due_date,
            status=ComplianceStatus.PENDING,
            rejection_reason=None,
            submitted_at=None,
            verified_at=None,
            verified_by_user_id=None,
        )
        db.add(record)
        db.flush()  # assign record.id

        # Audit initial creation
        history = ComplianceHistory(
            compliance_record_id=record.id,
            action="CREATED",
            from_status=None,
            to_status=ComplianceStatus.PENDING.value,
            remarks="Compliance record created",
            acted_by_user_id=user.id,
        )
        db.add(history)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_compliance_record(
        db: Session,
        compliance_id: uuid.UUID,
        user: User,
    ) -> ComplianceRecord:
        """
        Retrieve compliance record with documents, histories, and related entities.
        Enforces institutional isolation for institution users.
        """
        record = db.scalar(
            select(ComplianceRecord)
            .options(
                joinedload(ComplianceRecord.institution),
                joinedload(ComplianceRecord.application),
                joinedload(ComplianceRecord.verified_by_user),
                joinedload(ComplianceRecord.documents),
                joinedload(ComplianceRecord.histories).joinedload(ComplianceHistory.acted_by_user),
            )
            .where(ComplianceRecord.id == compliance_id)
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Compliance record '{compliance_id}' not found.",
            )

        # Access authorization
        if user.role == UserRole.INSTITUTION_USER:
            if record.institution_id != user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Compliance record '{compliance_id}' not found.",
                )
        elif user.role == UserRole.REVIEWER:
            # If application is attached, check reviewer assignment; otherwise reject
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reviewers cannot access unassigned compliance records.",
            )

        return record

    @staticmethod
    def list_compliance_records(
        db: Session,
        user: User,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        compliance_type: Optional[str] = None,
        institution_id: Optional[uuid.UUID] = None,
        application_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[ComplianceRecord], int, int, int, int]:
        """
        List compliance records with strict role-based data isolation.
        """
        base_query = (
            select(ComplianceRecord)
            .options(
                joinedload(ComplianceRecord.institution),
                joinedload(ComplianceRecord.application),
                joinedload(ComplianceRecord.verified_by_user),
                joinedload(ComplianceRecord.documents),
            )
        )

        filters = []

        if user.role == UserRole.INSTITUTION_USER:
            if not user.institution_id:
                return [], 0, page, page_size, 0
            filters.append(ComplianceRecord.institution_id == user.institution_id)
        elif user.role in [UserRole.ADMIN, UserRole.AICTE_OFFICIAL]:
            if institution_id:
                filters.append(ComplianceRecord.institution_id == institution_id)
        elif user.role == UserRole.REVIEWER:
            # Assignment logic not yet present: return empty collection
            return [], 0, page, page_size, 0

        if status_filter:
            filters.append(ComplianceRecord.status == status_filter)
        if compliance_type:
            filters.append(ComplianceRecord.compliance_type == compliance_type)
        if application_id:
            filters.append(ComplianceRecord.application_id == application_id)
        if search:
            search_term = f"%{search.strip()}%"
            filters.append(
                or_(
                    ComplianceRecord.title.ilike(search_term),
                    ComplianceRecord.compliance_type.ilike(search_term),
                    ComplianceRecord.description.ilike(search_term),
                )
            )

        if filters:
            base_query = base_query.where(*filters)

        # Count total
        count_stmt = select(func.count(ComplianceRecord.id))
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = db.scalar(count_stmt) or 0

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size

        records = list(
            db.scalars(
                base_query.order_by(ComplianceRecord.created_at.desc())
                .offset(offset)
                .limit(page_size)
            ).unique().all()
        )

        return records, total, page, page_size, total_pages

    @staticmethod
    def update_compliance_record(
        db: Session,
        compliance_id: uuid.UUID,
        user: User,
        payload: ComplianceRecordUpdate,
    ) -> ComplianceRecord:
        """
        Update a compliance record.
        Only institution user who owns the record can update, and only in PENDING or REJECTED status.
        """
        if user.role != UserRole.INSTITUTION_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only institution users can update their compliance records.",
            )

        record = db.scalar(select(ComplianceRecord).where(ComplianceRecord.id == compliance_id))
        if not record or record.institution_id != user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Compliance record '{compliance_id}' not found.",
            )

        if record.status not in [ComplianceStatus.PENDING, ComplianceStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update compliance record in '{record.status}' status. "
                       f"Only PENDING or REJECTED records can be modified.",
            )

        if payload.application_id and payload.application_id != record.application_id:
            target_app = db.scalar(
                select(Application).where(Application.id == payload.application_id)
            )
            if not target_app or target_app.institution_id != user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Application '{payload.application_id}' not found or belongs to another institution.",
                )
            record.application_id = payload.application_id

        if payload.compliance_type is not None:
            record.compliance_type = payload.compliance_type.strip()
        if payload.title is not None:
            record.title = payload.title.strip()
        if payload.description is not None:
            record.description = payload.description.strip()
        if payload.due_date is not None:
            record.due_date = payload.due_date

        history = ComplianceHistory(
            compliance_record_id=record.id,
            action="UPDATED",
            from_status=record.status.value if hasattr(record.status, "value") else str(record.status),
            to_status=record.status.value if hasattr(record.status, "value") else str(record.status),
            remarks="Compliance record updated by institution user",
            acted_by_user_id=user.id,
        )
        db.add(history)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def submit_compliance_record(
        db: Session,
        compliance_id: uuid.UUID,
        user: User,
    ) -> ComplianceRecord:
        """
        Submit a compliance record for statutory verification.
        Validates configurable requirements (e.g., mandatory supporting documents).
        """
        if user.role != UserRole.INSTITUTION_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only institution users can submit compliance records.",
            )

        record = db.scalar(
            select(ComplianceRecord)
            .options(joinedload(ComplianceRecord.documents))
            .where(ComplianceRecord.id == compliance_id)
        )
        if not record or record.institution_id != user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Compliance record '{compliance_id}' not found.",
            )

        if record.status in [ComplianceStatus.SUBMITTED, ComplianceStatus.VERIFIED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Compliance record is already {record.status}.",
            )

        # Check configurable requirements
        requirements = db.scalars(
            select(ComplianceRequirement).where(
                ComplianceRequirement.compliance_type == record.compliance_type,
                ComplianceRequirement.is_active.is_(True),
                ComplianceRequirement.is_required.is_(True),
            )
        ).all()

        for req in requirements:
            # If the requirement specifies allowed_document_types and requires them
            if req.allowed_document_types:
                existing_doc_types = {d.document_type for d in record.documents}
                matched = any(dt in existing_doc_types for dt in req.allowed_document_types)
                if not matched:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Mandatory requirement '{req.name}' requires at least one supporting document "
                            f"of type: {', '.join(req.allowed_document_types)}."
                        ),
                    )
            elif not record.documents:
                # Requirement requires documents generally
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Mandatory requirement '{req.name}' requires at least one uploaded document.",
                )

        old_status = record.status.value if hasattr(record.status, "value") else str(record.status)
        record.status = ComplianceStatus.SUBMITTED
        record.submitted_at = datetime.now(timezone.utc)
        record.rejection_reason = None

        history = ComplianceHistory(
            compliance_record_id=record.id,
            action="SUBMITTED",
            from_status=old_status,
            to_status=ComplianceStatus.SUBMITTED.value,
            remarks="Submitted for official verification",
            acted_by_user_id=user.id,
        )
        db.add(history)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def verify_compliance_record(
        db: Session,
        compliance_id: uuid.UUID,
        user: User,
        remarks: Optional[str] = None,
    ) -> ComplianceRecord:
        """
        Verify a submitted compliance record.
        Only ADMIN or AICTE_OFFICIAL can verify.
        Does NOT automatically approve an application.
        """
        if user.role not in [UserRole.ADMIN, UserRole.AICTE_OFFICIAL]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only AICTE officials and administrators can verify compliance submissions.",
            )

        record = db.scalar(select(ComplianceRecord).where(ComplianceRecord.id == compliance_id))
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Compliance record '{compliance_id}' not found.",
            )

        # Must be in SUBMITTED or UNDER_VERIFICATION status
        if record.status not in [ComplianceStatus.SUBMITTED, ComplianceStatus.UNDER_VERIFICATION]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Compliance record in status '{record.status}' cannot be verified. "
                       f"Must be SUBMITTED or UNDER_VERIFICATION.",
            )

        old_status = record.status.value if hasattr(record.status, "value") else str(record.status)
        now_utc = datetime.now(timezone.utc)

        record.status = ComplianceStatus.VERIFIED
        record.verified_at = now_utc
        record.verified_by_user_id = user.id
        record.rejection_reason = None

        history = ComplianceHistory(
            compliance_record_id=record.id,
            action="VERIFIED",
            from_status=old_status,
            to_status=ComplianceStatus.VERIFIED.value,
            remarks=remarks.strip() if remarks else "Compliance verified by official",
            acted_by_user_id=user.id,
        )
        db.add(history)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def reject_compliance_record(
        db: Session,
        compliance_id: uuid.UUID,
        user: User,
        reason: str,
    ) -> ComplianceRecord:
        """
        Reject a compliance submission with a mandatory reason.
        Allows the institution to correct and resubmit.
        """
        if user.role not in [UserRole.ADMIN, UserRole.AICTE_OFFICIAL]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only AICTE officials and administrators can reject compliance submissions.",
            )

        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid rejection reason must be provided.",
            )

        record = db.scalar(select(ComplianceRecord).where(ComplianceRecord.id == compliance_id))
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Compliance record '{compliance_id}' not found.",
            )

        old_status = record.status.value if hasattr(record.status, "value") else str(record.status)
        record.status = ComplianceStatus.REJECTED
        record.rejection_reason = reason.strip()

        history = ComplianceHistory(
            compliance_record_id=record.id,
            action="REJECTED",
            from_status=old_status,
            to_status=ComplianceStatus.REJECTED.value,
            remarks=f"Rejected: {reason.strip()}",
            acted_by_user_id=user.id,
        )
        db.add(history)
        db.commit()
        db.refresh(record)
        return record
