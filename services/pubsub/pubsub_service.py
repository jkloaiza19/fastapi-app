from abc import ABC, abstractmethod
from fastapi import Depends
import asyncio
from typing import Annotated

import aioredis
import json
from services.web_sockets.ws_manager import WSClientInterface, ws_manager_dep
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class PubSubServiceInterface(ABC):
    @abstractmethod
    async def publish(self, channel: str, message: dict) -> None:
        """Publish a message to a Redis channel."""
        pass

    @abstractmethod
    async def subscribe(self, channel: str) -> None:
        """Subscribe to a Redis channel."""
        pass

    @abstractmethod
    async def publish_to_redis(self, message: dict):
        """Publish a message to a Redis channel."""
        pass

    @abstractmethod
    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a Redis channel."""
        pass


class PubSubService(PubSubServiceInterface):
    def __init__(self, redis_client: aioredis.Redis, ws_client: WSClientInterface):
        self.redis_client = redis_client
        self.subscriber = self.redis_client.pubsub()
        self.ws_client = ws_client

    async def publish(self, channel: str, message: dict) -> None:
        """Publish a message to a Redis channel."""
        await self.redis_client.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str) -> None:
        """Subscribe to a Redis channel."""
        await self.subscriber.subscribe(settings.REDIS_CHANNEL)

        async for message in self.subscriber.listen():
            if message["type"] == "message":
                payload = json.loads(message["data"])
                await self.ws_manager.broadcast(payload)

    async def publish_to_redis(self, message: dict):
        await self.redis_client.publish(settings.REDIS_CHANNEL, json.dumps(message))

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a Redis channel."""
        await self.subscriber.unsubscribe(channel)


async def get_pubsub_service(
    ws_client: WSClientInterface = ws_manager_dep,
) -> PubSubServiceInterface:
    """Dependency to provide PubSubService."""
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL)
        pubsub_service = PubSubService(redis_client, ws_client)
        return pubsub_service
    except Exception as e:
        logger.error(f"Error initializing PubSubService: {e}")
        raise e


pubsub_dep = Annotated[PubSubServiceInterface, Depends(get_pubsub_service)]