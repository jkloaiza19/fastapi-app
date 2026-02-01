from abc import ABC, abstractmethod
from fastapi import Depends
from typing import Dict, Optional, AsyncGenerator, Union, Annotated
import json
import redis.asyncio as redis
from redis.asyncio import Redis as AsyncRedis
from core.logger import get_logger
from core.config import settings

logger = get_logger(__name__)
expire = 300


class RedisClientInterface(ABC):
    @abstractmethod
    async def get_cached_data(self, key: str) -> Optional[Union[str, int, bool, Dict]]:
        pass

    @abstractmethod
    async def set_cache_data(self, key: str, value: Optional[Union[str, int, bool, Dict]]):
        pass


class RedisClient(RedisClientInterface):
    def __init__(self, redis_url: str):
        self.__redis_client: AsyncRedis = redis.from_url(redis_url)

    async def get_cached_data(self, key: str) -> Optional[Dict]:
        try:
            data = await self.__redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving cache for {key}: {e}")
            return None

    async def set_cache_data(self, key: str, value: Optional[Union[str, int, bool, Dict]], ttl_sec: int = expire):
        try:
            await self.__redis_client.set(name=key, value=json.dumps(value), ex=ttl_sec)
        except Exception as e:
            logger.error(f"Error setting cache for {key}: {e}")


async def get_redis_client() -> AsyncGenerator[RedisClientInterface, None]:
    client = RedisClient(settings.REDIS_URL)
    try:
        yield client
    except Exception as e:
        logger.error(f"Error in Redis client: {e}")
        raise e
    finally:
        await client._RedisClient__redis_client.aclose()


redis_dep = Annotated[RedisClientInterface, Depends(get_redis_client)]
