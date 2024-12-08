from http.client import HTTPException

import redis.asyncio as redis
from redis import Redis

from core.logger import get_logger
from core.config import settings
from typing import Dict, Optional, AsyncGenerator
import json

from services.redis.redis_client_interface import RedisClientInterface

logger = get_logger(__name__)
expire = 300


class RedisClient(RedisClientInterface):
    def __init__(self, redis_url: str):
        pool = redis.ConnectionPool.from_url(redis_url)
        print(f"Redis URL: {redis_url}")
        self.redis_client: Redis = redis.Redis(connection_pool=pool).client()

    async def get_cached_data(self, key: str) -> Optional[Dict]:
        print(f"Ping successful: {await self.redis_client.ping()}")
        data = await self.redis_client.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_cache_data(self, key: str, value: Optional[str | int | bool | Dict]):
        await self.redis_client.set(name=key, value=json.dumps(value), ex=expire)


async def get_redis_client() -> AsyncGenerator[RedisClientInterface, None]:
    try:
        redis_client = RedisClient(settings.REDIS_URL)
        yield redis_client
    except Exception as e:
        logger.error(f"{str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize Redis service. {str(e)}")