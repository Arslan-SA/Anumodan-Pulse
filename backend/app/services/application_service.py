"""
AICTE FlowOps — Application Service

Encapsulates application lifecycle and authorization logic:
- Auto-generation of standardized application numbers
- Draft creation strictly bound to authenticated institution
- Institution-level data isolation for application queries
- Validation of draft-only edits and submissions
- Safe deletion of un-submitted drafts
"""

from datetime import datetime, timezone
import math
import secrets
from typing import List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application
from app.models.enums import ApplicationStatus, UserRole
from app.models.institution import Institution
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationUpdate


class ApplicationService:

    @staticmethod
    def generate_application_number(db: Session, academic_year: str) -> str:
        """
        Generate a unique statutory application number.
        Format: APP-{clean_year}-{random_token}
        Example: APP-2026-A8F3K2
        """
        clean_year = academic_year.replace("/", "-").replace(" ", "").split("-")[0]
        while True:
            token = secrets.token_hex(3).upper()
            candidate = f"APP-{clean_year}-{token}"
            exists = db.scalar(
                select(func.count(Application.id)).where(
                    Application.application_number == candidate
                )
            )
            if not exists:
                return candidate

    @staticmethod
    def create_draft_application(
        db: Session,
        user: User,
        payload: ApplicationCreate,
    ) -> Application:
        """
        Create a new application in DRAFT status.
        Only INSTITUTION_USER can create applications, strictly linked to their institution.
        """
        if user.role != UserRole.INSTITUTION_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only institution representatives can submit approval applications.",
            )

        if not user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is not linked to any registered institution.",
            )

        # Verify institution exists
        institution = db.get(Institution, user.institution_id)
        if not institution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Linked institution record not found.",
            )

        app_number = ApplicationService.generate_application_number(db, payload.academic_year)

        new_app = Application(
            application_number=app_number,
            institution_id=institution.id,
            application_type=payload.application_type.strip(),
            academic_year=payload.academic_year.strip(),
            status=ApplicationStatus.DRAFT,
            current_stage=None,
            submitted_at=None,
        )

        db.add(new_app)
        db.commit()
        db.refresh(new_app)
        return new_app

    @staticmethod
    def get_application_for_user(
        db: Session,
        application_id: uuid.UUID,
        user: User,
    ) -> Application:
        """
        Retrieve an application while enforcing strict institutional isolation.
        Institution users can only see their own applications; 404 is returned
        for other applications to avoid data enumeration.
        """
        app = db.scalar(
            select(Application)
            .options(joinedload(Application.institution))
            .where(Application.id == application_id)
        )
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' was not found.",
            )

        # Role-based access boundary
        if user.role == UserRole.INSTITUTION_USER:
            if app.institution_id != user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Application with ID '{application_id}' was not found.",
                )
        elif user.role in [UserRole.ADMIN, UserRole.AICTE_OFFICIAL]:
            # Officials and Admins have global visibility
            pass
        elif user.role == UserRole.REVIEWER:
            # Reviewer assignment logic will be implemented in Phase 5; reject unassigned access
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' is not assigned to this reviewer.",
            )

        return app

    @staticmethod
    def list_applications_for_user(
        db: Session,
        user: User,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[ApplicationStatus] = None,
        application_type: Optional[str] = None,
        academic_year: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Application], int, int]:
        """
        Paginated listing of applications scoped by user role.
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        # Reviewers without assignment logic see empty list
        if user.role == UserRole.REVIEWER:
            return [], 0, 1

        query = select(Application).options(joinedload(Application.institution))
        count_query = select(func.count(Application.id))

        # Institution users see ONLY their own institution's applications
        if user.role == UserRole.INSTITUTION_USER:
            if not user.institution_id:
                return [], 0, 1
            query = query.where(Application.institution_id == user.institution_id)
            count_query = count_query.where(Application.institution_id == user.institution_id)

        # Common filters
        if status_filter:
            query = query.where(Application.status == status_filter)
            count_query = count_query.where(Application.status == status_filter)

        if application_type:
            query = query.where(Application.application_type.ilike(f"%{application_type.strip()}%"))
            count_query = count_query.where(Application.application_type.ilike(f"%{application_type.strip()}%"))

        if academic_year:
            query = query.where(Application.academic_year == academic_year.strip())
            count_query = count_query.where(Application.academic_year == academic_year.strip())

        # Search across application number or institution name (for admins/officials)
        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.join(Application.institution).where(
                or_(
                    Application.application_number.ilike(search_pattern),
                    Institution.institution_name.ilike(search_pattern),
                )
            )
            count_query = count_query.join(Application.institution).where(
                or_(
                    Application.application_number.ilike(search_pattern),
                    Institution.institution_name.ilike(search_pattern),
                )
            )

        total_count = db.scalar(count_query) or 0
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

        offset = (page - 1) * page_size
        items = db.scalars(
            query.order_by(Application.created_at.desc()).offset(offset).limit(page_size)
        ).unique().all()

        return items, total_count, total_pages

    @staticmethod
    def update_draft_application(
        db: Session,
        application_id: uuid.UUID,
        user: User,
        payload: ApplicationUpdate,
    ) -> Application:
        """
        Update an application. Only the owning institution user can edit, and only when in DRAFT status.
        """
        app = ApplicationService.get_application_for_user(db, application_id, user)

        if user.role != UserRole.INSTITUTION_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only institution users can modify application drafts.",
            )

        app_status_val = app.status.value if hasattr(app.status, "value") else str(app.status)
        if app_status_val != ApplicationStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit application in '{app_status_val}' status. Only DRAFT applications can be modified.",
            )

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(app, field, value.strip() if isinstance(value, str) else value)

        db.commit()
        db.refresh(app)
        return app

    @staticmethod
    def submit_draft_application(
        db: Session,
        application_id: uuid.UUID,
        user: User,
    ) -> Application:
        """
        Submit a DRAFT application. Transitions status to SUBMITTED and sets submitted_at.
        """
        app = ApplicationService.get_application_for_user(db, application_id, user)

        if user.role != UserRole.INSTITUTION_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only institution users can submit applications.",
            )

        app_status_val = app.status.value if hasattr(app.status, "value") else str(app.status)
        if app_status_val != ApplicationStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit application in '{app_status_val}' status. Only DRAFT applications can be submitted.",
            )

        # Initialize workflow progression and initial stage history atomically
        from app.services.workflow_service import WorkflowService
        WorkflowService.initialize_application_workflow(db, app, user)

        db.commit()
        db.refresh(app)

        # Trigger notification event
        from app.services.notification_service import NotificationService
        NotificationService.notify_application_submitted(db, app, user)

        return app


    @staticmethod
    def delete_draft_application(
        db: Session,
        application_id: uuid.UUID,
        user: User,
    ) -> None:
        """
        Delete a DRAFT application. Non-draft / submitted applications can never be deleted.
        """
        app = ApplicationService.get_application_for_user(db, application_id, user)

        if user.role != UserRole.INSTITUTION_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only institution users can delete application drafts.",
            )

        app_status_val = app.status.value if hasattr(app.status, "value") else str(app.status)
        if app_status_val != ApplicationStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete application in '{app_status_val}' status. Submitted applications cannot be deleted.",
            )

        db.delete(app)
        db.commit()
