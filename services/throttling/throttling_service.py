from typing import Annotated

from fastapi import Request, Depends
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import asyncio

request_per_second = 5


class ThrottlingServiceInterface(ABC):
    @abstractmethod
    async def is_allowed(self, request: Request) -> bool:
        """Check if the request is allowed based on throttling rules."""
        pass

    @abstractmethod
    async def acquire(self) -> None:
        """Record the request for throttling purposes."""
        pass


class ThrottlingService(ThrottlingServiceInterface):
    def __init__(self, rate_per_second: float):
        self.rate_per_second = rate_per_second
        self.last_request_time = datetime.now()
        self.lock = asyncio.Lock()

    async def is_allowed(self, request: Request) -> bool:
        async with self.lock:
            now = datetime.now()
            time_passed = (now - self.last_request_time).total_seconds()
            if time_passed >= 1 / self.rate_per_second:
                return True
            return False

    async def acquire(self):
        async with self.lock:
            now = datetime.now()
            time_passed = (now - self.last_request_time).total_seconds()
            if time_passed < 1 / self.rate_per_second:
                sleep_time = 1 / self.rate_per_second - time_passed
                await asyncio.sleep(sleep_time)
            self.last_request_time = datetime.now()


def get_throttling_service() -> ThrottlingService:
    return ThrottlingService(rate_per_second=request_per_second)


throttling_service_dep = Annotated[ThrottlingServiceInterface, Depends(get_throttling_service)]
