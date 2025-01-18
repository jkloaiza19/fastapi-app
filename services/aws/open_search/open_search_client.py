# https://opensearch.org/docs/latest/clients/python-low-level/
from abc import ABC, abstractmethod
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import ConnectionError, OpenSearchException
from concurrent.futures import ThreadPoolExecutor
import asyncio
from typing import Optional, AsyncGenerator, Dict, Any
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class OpenSearchClientInterface(ABC):
    @abstractmethod
    def run_in_thread(self, func, *args, **kwargs):
        pass

    @abstractmethod
    async def create_index(self, index_name: str, index_body: Optional[dict] = {}) -> None:
        pass

    @abstractmethod
    async def delete_index(self, index_name: str) -> None:
        pass

    @abstractmethod
    async def index_document(self, index_name: str, document: dict) -> None:
        pass

    @abstractmethod
    async def search(self, index_name: str, query: dict) -> dict:
        pass

    # @abstractmethod
    # def get_document(self, index_name: str, document_id: str) -> Optional[dict]:
    #     pass
    #

    @abstractmethod
    def close(self):
        pass


class OpenSearchClient(OpenSearchClientInterface):
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.loop = asyncio.get_event_loop()
        self.client = OpenSearch(
            hosts=[{
                'host': settings.OPENSEARCH_HOST,
                'port': settings.OPENSEARCH_PORT
            }],
            http_compress=True,
            http_auth=(settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD),
            use_ssl=True,
            verify_certs=True,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            connection_class=RequestsHttpConnection
        )

    async def run_in_thread(self, func, *args, **kwargs):
        """Run a blocking function in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))

    async def create_index(self, index_name: str, index_body: Optional[dict] = {}) -> None:
        """Create an OpenSearch index."""
        try:
            index_exists = await self.run_in_thread(self.client.indices.exists, index_name)
            if not index_exists:
                response = await self.run_in_thread(self.client.indices.create, index_name, index_body)
                return response
            else:
                raise OpenSearchException(f"Index {index_name} already exists.")
        except OpenSearchException as e:
            logger.error(f"Error creating index: {e}")
            raise e

    async def delete_index(self, index_name: str) -> None:
        try:
            await self.run_in_thread(self.client.indices.delete, index_name)
        except OpenSearchException as e:
            logger.error(f"Error deleting index: {e}")
            raise e

    async def index_document(self, index_name: str, document: dict) -> None:
        try:
            response = await self.run_in_thread(
                self.client.index,
                index=index_name,
                body=document
            )
            return response
        except OpenSearchException as e:
            logger.error(f"Error indexing document: {e}")
            raise e

    async def search(self, index_name: str, query: dict) -> dict:
        try:
            response = await self.run_in_thread(
                self.client.search,
                index=index_name,
                body=query
            )
            return response
        except OpenSearchException as e:
            logger.error(f"Error searching index: {e}")
            raise e

    def close(self):
        self.client.close()


def get_opensearch_client() -> AsyncGenerator[OpenSearchClientInterface, None]:
    try:
        open_search_client = OpenSearchClient()
        yield open_search_client
    except ConnectionError as e:
        logger.error(f"Error connecting to OpenSearch: {e}")
        raise e
    finally:
        open_search_client.close()
