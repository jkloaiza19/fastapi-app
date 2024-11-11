from json import JSONDecodeError
from core.logger import get_logger
from httpx import AsyncClient, HTTPStatusError, Timeout, Limits, RequestError, Response
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from typing import Dict, Any, Optional, AsyncGenerator
from abc import ABC, abstractmethod

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


class RetryDecorator:
    @staticmethod
    def get_retry_decorator():
        """Returns a retry decorator with a consistent retry strategy."""
        return retry(
            retry=retry_if_exception_type((HTTPStatusError, RequestError)),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            stop=stop_after_attempt(3)
        )


class HttpClient(HttpClientInterface, ABC):
    def __init__(self):
        self.async_client = AsyncClient(timeout=Timeout(10.0), limits=Limits(max_connections=10))
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

    @RetryDecorator.get_retry_decorator()
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

    @RetryDecorator.get_retry_decorator()
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


async def get_http_client() -> AsyncGenerator[HttpClient, None]:
    async_client = AsyncClient(
        timeout=Timeout(30.0),
        limits=Limits(max_connections=100, max_keepalive_connections=10)
    )
    http_client = HttpClient(client=async_client)
    try:
        yield http_client
    except HTTPStatusError as e:
        logger.error(f"{str(e)}")
        raise e
    finally:
        await async_client.aclose()
