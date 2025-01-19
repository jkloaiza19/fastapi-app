from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio


class ThreadingUtilInterface(ABC):
    @abstractmethod
    async def run_in_thread(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        pass


class ThreadingUtil(ThreadingUtilInterface):
    def __init__(self, max_workers: Optional[int] = 1) -> None:
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.loop = asyncio.get_event_loop()

    async def run_in_thread(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        """Run a blocking function in a thread pool."""
        return await self.loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))


def get_threading_util() -> ThreadingUtilInterface:
    return ThreadingUtil()
