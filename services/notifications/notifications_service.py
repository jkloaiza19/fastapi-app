from abc import ABC, abstractmethod
from typing import AsyncGenerator, Annotated
from fastapi import Depends, Request

from db.database_repository import DataBaseRepositoryInterface, notifications_repository_dep
from db.models import Notifications
from services.web_sockets.ws_manager import WSClientInterface, ws_manager_dep
from schemas.notification_schema import NotificationRequest, NotificationResponse
from core.logger import get_logger
from schemas import ResponseWithPagination
from utils.pagination_util import generate_pagination, get_base_url

logger = get_logger(__name__)


class NotificationsServiceInterface(ABC):
    """Interface for Notifications Service."""
    @abstractmethod
    async def get_paginated_notifications(self, request: Request, limit: int = 0, offset: int = 0) -> list:
        """Get all notifications."""
        pass

    @abstractmethod
    async def send_notification(self, notification: NotificationRequest) -> None:
        """Send a notification to a user."""
        pass

    @abstractmethod
    async def get_notifications(self, user_id: int) -> list:
        """Get all notifications for a user."""
        pass

    @abstractmethod
    async def mark_as_read(self, notification_id: int, repository: DataBaseRepositoryInterface) -> None:
        """Mark a notification as read."""
        pass


class NotificationsService(NotificationsServiceInterface):
    def __init__(self, repository: DataBaseRepositoryInterface, ws_client: WSClientInterface):
        self.repository = repository
        self.ws_client = ws_client

    async def get_paginated_notifications(
            self,
            request: Request,
            limit: int = 0,
            offset: int = 0
    ) -> ResponseWithPagination:
        try:
            print(f"Request: {request.method}")
            notifications = await self.repository.get_all(limit=limit, offset=offset)
            total_notifications = await self.repository.get_total_count()

            if not notifications or not total_notifications:
                raise Exception("No notifications found")

            paginated_notifications = generate_pagination(
                page=offset,
                total_items=total_notifications,
                page_size=limit,
                base_url=get_base_url(request),
                method=request.method,
            )

            return ResponseWithPagination(
                pagination=paginated_notifications,
                results=notifications,
            )
        except Exception as e:
            logger.error(f"Error fetching notifications: {e}")
            raise e

    async def send_notification(
            self,
            notification: NotificationRequest,
    ) -> None:
        new_notif: Notifications = await self.repository.create_one(notification.model_dump())
        if new_notif:
            await self.ws_client.broadcast({"message": "New notification", "data": new_notif.to_dict(exclude={"created_at"})})
            return NotificationResponse(**new_notif.to_dict())
        else:
            raise Exception("Failed to send notification")

    async def get_notifications(self, user_id: int) -> list:
        notifications = await self.repository.find_by_query(f"SELECT * FROM notifications WHERE user_id={user_id}")
        return notifications

    async def mark_as_read(self, notification_id: int) -> None:
        notification = await self.repository.find_by_query(
            f"SELECT * FROM notifications WHERE id={notification_id}")
        if notification is None:
            raise Exception("Notification not found")

        notification.is_read = True
        await self.repository.update_one(notification)


async def get_notifications_service(
        notifications_repo: notifications_repository_dep,
        ws_client: ws_manager_dep
) -> AsyncGenerator[NotificationsServiceInterface, None]:
    try:
        service = NotificationsService(repository=notifications_repo, ws_client=ws_client)
        yield service
    except Exception as e:
        logger.error(f"Error initializing notifications service: {e}")
        raise e


notifications_service_dep = Annotated[NotificationsServiceInterface, Depends(get_notifications_service)]
