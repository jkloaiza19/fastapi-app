from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse
from core.logger import get_logger
from api.dependencies import user_repository_dep
from schemas.notification_schema import NotificationRequest, NotificationResponse
from typing import Dict
from api.dependencies import redis_dep
from db.database_repository import notifications_repository_dep
from services.web_sockets.ws_manager import ws_manager_dep
from services.notifications.notifications_service import notifications_service_dep

logger = get_logger(__name__)
router = APIRouter()


@router.get("/all", status_code=status.HTTP_200_OK)
async def get_all_notifications(
        request: Request,
        notifications_service: notifications_service_dep,
        limit: int = 0,
        offset: int = 0,
):
    notifications = await notifications_service.get_paginated_notifications(limit=limit, offset=offset, request=request)
    return notifications


@router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def get_user(
        user_id: int,
        notifications_rep: notifications_repository_dep,
        redis: redis_dep
):
    return await notifications_rep.find_unique(redis=redis, id=user_id)


@router.post("/send", status_code=status.HTTP_201_CREATED, response_model=NotificationResponse)
async def send_notification(
        notification: NotificationRequest,
        notifications_service: notifications_service_dep
):
    return await notifications_service.send_notification(
        notification=notification,
    )


@router.post("/update", status_code=status.HTTP_200_OK)
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
