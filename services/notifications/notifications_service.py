from abc import ABC, abstractmethod
from typing import AsyncGenerator, Annotated
from fastapi import Depends

from db.database_repository import DataBaseRepositoryInterface, notifications_repository_dep
from db.models import Notifications
from services.web_sockets.ws_manager import WSClientInterface, ws_manager_dep
from schemas.notification_schema import NotificationRequest, NotificationResponse
from core.logger import get_logger

logger = get_logger(__name__)


class NotificationsServiceInterface(ABC):
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
