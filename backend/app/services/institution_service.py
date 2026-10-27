"""
AICTE FlowOps — Institution Service

Encapsulates business operations for technical institutions:
- Profile retrieval for authenticated institution users
- Permitted profile updates
- Cross-institution search, filtering, and pagination for officials
"""

import math
from typing import List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.institution import Institution
from app.models.user import User
from app.schemas.institution import InstitutionUpdate


class InstitutionService:

    @staticmethod
    def get_institution_by_id(db: Session, institution_id: uuid.UUID) -> Institution:
        """Retrieve an institution by ID or raise 404."""
        institution = db.get(Institution, institution_id)
        if not institution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Institution with ID '{institution_id}' was not found.",
            )
        return institution

    @staticmethod
    def get_user_institution(db: Session, user: User) -> Institution:
        """
        Resolve the institution owned by the authenticated institution user.
        Strictly isolates institutional data.
        """
        if not user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is not linked to any technical institution.",
            )
        return InstitutionService.get_institution_by_id(db, user.institution_id)

    @staticmethod
    def update_user_institution(
        db: Session,
        user: User,
        payload: InstitutionUpdate,
    ) -> Institution:
        """
        Update permitted institutional profile fields.
        Guarantees that institution_id and institution_code cannot be modified.
        """
        institution = InstitutionService.get_user_institution(db, user)

        update_data = payload.model_dump(exclude_unset=True)
        # Explicit guard against immutable fields
        update_data.pop("id", None)
        update_data.pop("institution_code", None)

        for field, value in update_data.items():
            setattr(institution, field, value)

        db.commit()
        db.refresh(institution)
        return institution

    @staticmethod
    def list_institutions(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Tuple[List[Institution], int, int]:
        """
        Paginated directory of technical institutions with name/code search and state filter.
        Returns: (items, total_count, total_pages)
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        query = select(Institution)
        count_query = select(func.count(Institution.id))

        if search:
            search_filter = or_(
                Institution.institution_name.ilike(f"%{search.strip()}%"),
                Institution.institution_code.ilike(f"%{search.strip()}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if state:
            state_filter = Institution.state.ilike(f"%{state.strip()}%")
            query = query.where(state_filter)
            count_query = count_query.where(state_filter)

        total_count = db.scalar(count_query) or 0
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

        offset = (page - 1) * page_size
        items = db.scalars(
            query.order_by(Institution.created_at.desc()).offset(offset).limit(page_size)
        ).all()

        return items, total_count, total_pages
