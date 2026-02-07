from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse
from core.logger import get_logger
from schemas.notification_schema import NotificationRequest, NotificationResponse
from typing import Dict
from api.dependencies import redis_dep
from db.database_repository import notifications_repository_dep
from services.web_sockets.ws_manager import ws_manager_dep
from services.notifications.notifications_service import notifications_service_dep
from services.throttling.throttling_service import throttling_service_dep
from db.database_repository import user_repository_dep

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/all",
    status_code=status.HTTP_200_OK,
    summary="Get all notifications (paginated)",
    description="""Retrieve all notifications with optional pagination.
    
    **Pagination:**
    - `limit`: Maximum number of notifications to return (0 = no limit)
    - `offset`: Number of notifications to skip (for pagination)
    
    **Returns:** List of notifications with pagination metadata including:
    - Total count of notifications
    - Current page information
    - Notification details (ID, message, status, timestamps)
    
    **Example:** `GET /notifications/all?limit=20&offset=0` returns first 20 notifications
    """,
    responses={
        200: {"description": "Notifications retrieved successfully"}
    }
)
async def get_all_notifications(
        request: Request,
        notifications_service: notifications_service_dep,
        limit: int = 0,
        offset: int = 0,
):
    notifications = await notifications_service.get_paginated_notifications(limit=limit, offset=offset, request=request)
    return notifications


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Get notification by ID",
    description="""Retrieve a specific notification by its ID.
    
    **Features:**
    - Rate limited using throttling service
    - Results cached in Redis for performance
    
    **Returns:** Complete notification details including:
    - Notification ID and message content
    - Read/unread status
    - Associated user ID
    - Creation and update timestamps
    """,
    responses={
        200: {"description": "Notification found and returned"},
        404: {"description": "Notification not found"},
        429: {"description": "Rate limit exceeded"}
    }
)
async def get_user(
        user_id: int,
        notifications_rep: notifications_repository_dep,
        redis: redis_dep,
        throttling_service: throttling_service_dep,
):
    await throttling_service.acquire()
    return await notifications_rep.find_unique(redis=redis, id=user_id)


@router.post(
    "/send",
    status_code=status.HTTP_201_CREATED,
    response_model=NotificationResponse,
    summary="Send a notification",
    description="""Create and send a new notification to a user.
    
    The notification will be:
    - Saved to the database
    - Sent via WebSocket to connected clients (real-time)
    - Made available via the notifications API
    
    **Required fields:**
    - `user_id`: ID of the user to notify
    - `message`: Notification message content
    
    **Optional fields:**
    - `type`: Notification type/category
    - `metadata`: Additional JSON data
    """,
    responses={
        201: {"description": "Notification sent successfully"},
        400: {"description": "Invalid notification data"},
        404: {"description": "User not found"}
    }
)
async def send_notification(
        notification: NotificationRequest,
        notifications_service: notifications_service_dep
):
    return await notifications_service.send_notification(
        notification=notification,
    )


@router.post(
    "/update",
    status_code=status.HTTP_200_OK,
    summary="Mark notification as read",
    description="""Mark a notification as read/acknowledged.
    
    **Actions performed:**
    - Updates notification status in database
    - Invalidates related cache entries
    - Notifies connected WebSocket clients of the status change
    
    **Query Parameters:**
    - `notification_id`: ID of the notification to mark as read
    
    This is typically called when a user views or dismisses a notification.
    """,
    responses={
        200: {"description": "Notification marked as read"},
        404: {"description": "Notification not found"},
        500: {"description": "Failed to update notification"}
    }
)
async def update_notification(
        notification_id: int,
        notifications_rep: notifications_repository_dep,
        redis: redis_dep,
        ws_manager: ws_manager_dep,
        notifications_service: notifications_service_dep):
    print("Updating notification with ID:", notification_id)
    return await notifications_service.mark_as_read(
        notification_id=notification_id,
        repository=notifications_rep
    )
