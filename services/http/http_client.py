from json import JSONDecodeError
from core.logger import get_logger
from httpx import AsyncClient, HTTPStatusError, Timeout, Limits, RequestError, Response
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from typing import Dict, Any, Optional, AsyncGenerator
from abc import ABC, abstractmethod
from fastapi import HTTPException, status

logger = get_logger(__name__)


class HttpClientInterface(ABC):
    @property
    @abstractmethod
    def client(self):
        pass

    @abstractmethod
    async def handle_response(self):
        pass

    @abstractmethod
    async def post_request(self):
        pass

    @abstractmethod
    async def get_request(self):
        pass


class RetryDecoratorWrapper:
    @staticmethod
    def get_retry_decorator():
        """Returns a retry decorator with a consistent retry strategy."""
        return retry(
            retry=retry_if_exception_type((HTTPStatusError, RequestError)),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            stop=stop_after_attempt(3)
        )


class HttpClient(HttpClientInterface, ABC):
    def __init__(self, client: AsyncClient):
        # self.async_client = client or AsyncClient(timeout=Timeout(10.0), limits=Limits(max_connections=10))
        self.async_client = client
        self.common_headers = {"Content-Type": "application/json"}

    def client(self):
        return self.async_client

    async def handle_response(self, response: Response) -> Any:
        """Handles common response processing and error logging."""
        try:
            response.raise_for_status()
            data = response.json()
            return data
        except HTTPStatusError as e:
            logger.error(f"Error performing request: {str(e)}")
            raise e
        except (JSONDecodeError, TypeError) as e:
            logger.error(f"Error decoding JSON response: {str(e)}")
            raise e

    @RetryDecoratorWrapper.get_retry_decorator()
    async def post_request(
            self,
            url: str,
            data: Dict[str, Any],
            custom_headers: Optional[Dict[str, str]] = {},
    ) -> Any:
        """Sends a POST request with retries."""
        try:
            async with self.async_client as http_client:
                response = await http_client.post(
                    url=url,
                    json=data,
                    headers={
                        **self.common_headers,
                        **custom_headers,
                    }
                )
                return await self.handle_response(response)
        finally:
            if isinstance(self.async_client, AsyncClient):
                await self.async_client.aclose()

    @RetryDecoratorWrapper.get_retry_decorator()
    async def get_request(
            self,
            url: str,
            custom_headers: Optional[Dict[str, str]] = {},
    ) -> Any:
        """Sends a GET request with retries."""
        try:
            async with self.async_client as http_client:
                response = await http_client.get(
                    url,
                    headers={
                        **self.common_headers,
                        **custom_headers,
                    }
                )
                return await self.handle_response(response)
        finally:
            if isinstance(self.async_client, AsyncClient):
                await self.async_client.aclose()


class HttpClientSingleton:
    """Ensures that only one instance of HttpClient and its underlying AsyncClient is
    created and reused across the application"""
    _instance: Optional[HttpClient] = None
    _async_client: Optional[AsyncClient] = None

    @classmethod
    def get_instance(cls) -> HttpClient:
        if cls._instance is None:
            if cls._async_client is None:
                cls._async_client = AsyncClient(
                    timeout=Timeout(30.0),
                    limits=Limits(max_connections=100, max_keepalive_connections=10),
                )
            cls._instance = HttpClient(client=cls._async_client)
        return cls._instance

    @classmethod
    async def close_instance(cls):
        """Closes the AsyncClient instance."""
        if cls._async_client:
            await cls._async_client.aclose()
            cls._async_client = None
        cls._instance = None


async def get_http_client() -> AsyncGenerator[HttpClient, None]:
    http_client = HttpClientSingleton.get_instance()
    try:
        yield http_client
    except HTTPStatusError as e:
        logger.error(f"{str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")
    finally:
        await HttpClientSingleton.close_instance()
