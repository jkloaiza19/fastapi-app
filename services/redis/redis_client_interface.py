from abc import ABC, abstractmethod
from typing import Optional, Dict


class RedisClientInterface(ABC):

    async def get_cached_data(self, key: str) -> Optional[str | int | bool | Dict]:
        pass

    @abstractmethod
    async def set_cache_data(self, key: str, value: Optional[str | int | bool | Dict]):
        pass

