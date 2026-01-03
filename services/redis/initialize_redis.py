import json
from typing import Optional, Dict
from abc import ABC, abstractmethod

import redis.asyncio as redis
from redis import Redis
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

expire = 300


class RedisClientInitializerInterface(ABC):
    @abstractmethod
    def init_redis_service(self):
        pass

    @abstractmethod
    async def close(self):
        pass

    @abstractmethod
    def get_client(self) -> Redis:
        pass


class RedisClientInitializer(RedisClientInitializerInterface):
    def __init__(self, redis_url: str):
        self.redis_url: str = redis_url
        self.client: Redis = None

    def init_redis_service(self):
        """Initialize the Redis client with a connection pool."""
        pool = redis.ConnectionPool.from_url(self.redis_url)
        logger.info(f"Redis URL: {self.redis_url}")
        self.client = redis.Redis(connection_pool=pool).client()

    async def close(self):
        """Close the Redis client connection."""
        if self.client:
            await self.client.aclose()

    def get_client(self) -> Redis:
        """Get the Redis client instance."""
        if self.client is None:
            raise Exception("Redis is not initialized")
        return self.client


def get_redis() -> RedisClientInitializerInterface:
    redis_client = RedisClientInitializer(settings.REDIS_URL)
    return redis_client
