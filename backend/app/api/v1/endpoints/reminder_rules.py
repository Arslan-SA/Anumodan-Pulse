"""
AICTE FlowOps — Reminder Rules & Escalation Endpoints

Administrative management of reminder policies and escalation monitoring:
- GET    /api/v1/reminder-rules
- POST   /api/v1/reminder-rules
- PATCH  /api/v1/reminder-rules/{id}
- PATCH  /api/v1/reminder-rules/{id}/status
- GET    /api/v1/reminder-rules/escalations
"""

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_admin
from app.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.escalation import EscalationHistoryResponse
from app.schemas.reminder_rule import (
    ReminderRuleCreate,
    ReminderRuleResponse,
    ReminderRuleStatusUpdate,
    ReminderRuleUpdate,
)
from app.services.deadline_service import DeadlineService

router = APIRouter()


@router.get(
    "",
    response_model=List[ReminderRuleResponse],
    summary="List Reminder Rules",
)
def list_reminder_rules(
    active_only: bool = Query(False, description="Filter only active rules"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List configured reminder rules and deadline alerts."""
    rules = DeadlineService.list_reminder_rules(db=db, active_only=active_only)
    return [ReminderRuleResponse.model_validate(r) for r in rules]


@router.get(
    "/escalations",
    response_model=PaginatedResponse[EscalationHistoryResponse],
    summary="List Escalations",
)
def list_escalations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List deadline and inactivity escalation histories.
    Officials and Admins see cross-platform escalations; Institutions see their own.
    """
    items, total, curr_page, limit, total_pages = DeadlineService.list_escalations(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[
            EscalationHistoryResponse(
                id=e.id,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                rule_name=e.rule_name,
                escalation_level=e.escalation_level,
                escalated_to_role=e.escalated_to_role,
                escalated_to_user_id=e.escalated_to_user_id,
                escalated_to_name=e.escalated_to_user.full_name if e.escalated_to_user else None,
                reason=e.reason,
                created_at=e.created_at,
            )
            for e in items
        ],
        total=total,
        page=curr_page,
        page_size=limit,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=ReminderRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Reminder Rule",
)
def create_reminder_rule(
    payload: ReminderRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Configure a new reminder rule. Restricted to system administrators."""
    rule = DeadlineService.create_reminder_rule(db, current_user, payload)
    return ReminderRuleResponse.model_validate(rule)


@router.patch(
    "/{rule_id}",
    response_model=ReminderRuleResponse,
    summary="Update Reminder Rule",
)
def update_reminder_rule(
    rule_id: uuid.UUID,
    payload: ReminderRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update an existing reminder rule. Restricted to system administrators."""
    rule = DeadlineService.update_reminder_rule(db, current_user, rule_id, payload)
    return ReminderRuleResponse.model_validate(rule)


@router.patch(
    "/{rule_id}/status",
    response_model=ReminderRuleResponse,
    summary="Update Reminder Rule Status",
)
def update_reminder_rule_status(
    rule_id: uuid.UUID,
    payload: ReminderRuleStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Toggle activation of a reminder rule. Restricted to system administrators."""
    rule = DeadlineService.toggle_reminder_rule_status(db, current_user, rule_id, payload.is_active)
    return ReminderRuleResponse.model_validate(rule)
