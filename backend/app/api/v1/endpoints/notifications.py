"""
AICTE FlowOps — Notification Endpoints

Handles user notifications and alert management:
- GET    /api/v1/notifications                 (List user's notifications with pagination & filters)
- GET    /api/v1/notifications/unread-count    (Get unread notifications count)
- POST   /api/v1/notifications/mark-all-read   (Bulk mark all notifications as read)
- GET    /api/v1/notifications/{id}            (Get single notification detail)
- PATCH  /api/v1/notifications/{id}/read       (Mark notification as read)
- PATCH  /api/v1/notifications/{id}/archive    (Archive notification)
"""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.notification import (
    NotificationMarkReadResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[NotificationResponse],
    summary="List Notifications",
)
def list_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (UNREAD, READ, ARCHIVED)"),
    notification_type: Optional[str] = Query(None, description="Filter by notification type"),
    priority: Optional[str] = Query(None, description="Filter by priority (LOW, MEDIUM, HIGH, CRITICAL)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List notifications strictly scoped to the authenticated user.
    Admins cannot see other users' private notifications.
    """
    items, total, curr_page, limit, total_pages = NotificationService.list_user_notifications(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
        status_filter=status,
        notification_type=notification_type,
        priority=priority,
    )
    return PaginatedResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        page=curr_page,
        page_size=limit,
        total_pages=total_pages,
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCountResponse,
    summary="Get Unread Count",
)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return total count of UNREAD notifications for the authenticated user."""
    count = NotificationService.get_unread_count(db, current_user)
    return NotificationUnreadCountResponse(unread_count=count)


@router.post(
    "/mark-all-read",
    response_model=NotificationMarkReadResponse,
    summary="Mark All Notifications As Read",
)
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark all active UNREAD notifications for the authenticated user as READ."""
    updated = NotificationService.mark_all_as_read(db, current_user)
    return NotificationMarkReadResponse(success=True, updated_count=updated)


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get Notification Details",
)
def get_notification(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve single notification. Enforces recipient ownership."""
    notif = NotificationService.get_user_notification(db, notification_id, current_user)
    return NotificationResponse.model_validate(notif)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark Notification As Read",
)
def mark_as_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark a specific notification as READ with UTC timestamp."""
    notif = NotificationService.mark_as_read(db, notification_id, current_user)
    return NotificationResponse.model_validate(notif)


@router.patch(
    "/{notification_id}/archive",
    response_model=NotificationResponse,
    summary="Archive Notification",
)
def archive_notification(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Archive a notification."""
    notif = NotificationService.archive_notification(db, notification_id, current_user)
    return NotificationResponse.model_validate(notif)
