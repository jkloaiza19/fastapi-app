# https://opensearch.org/docs/latest/clients/python-low-level/
from abc import ABC, abstractmethod
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import ConnectionError, OpenSearchException
from typing import Optional, AsyncGenerator, Dict, Any
from core.config import settings
from core.logger import get_logger
from utils.run_in_thread_util import get_threading_util, ThreadingUtilInterface

logger = get_logger(__name__)


class OpenSearchClientInterface(ABC):
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

    @abstractmethod
    async def get_document(self, index_name: str, document_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def close(self):
        pass


class OpenSearchClient(OpenSearchClientInterface):
    def __init__(self, threading_util: ThreadingUtilInterface):
        self.threading_util = threading_util
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

    async def create_index(self, index_name: str, index_body: Optional[dict] = {}) -> None:
        """Create an OpenSearch index."""
        try:
            index_exists = await self.threading_util.run_in_thread(self.client.indices.exists, index_name)
            if not index_exists:
                response = await self.threading_util.run_in_thread(self.client.indices.create, index_name, index_body)
                return response
            else:
                raise OpenSearchException(f"Index {index_name} already exists.")
        except OpenSearchException as e:
            logger.error(f"Error creating index: {e}")
            raise e

    async def delete_index(self, index_name: str) -> None:
        try:
            await self.threading_util.run_in_thread(self.client.indices.delete, index_name)
        except OpenSearchException as e:
            logger.error(f"Error deleting index: {e}")
            raise e

    async def index_document(self, index_name: str, document: dict) -> None:
        try:
            response = await self.threading_util.run_in_thread(
                self.client.index,
                index=index_name,
                body=document
            )
            return response
        except OpenSearchException as e:
            logger.error(f"Error indexing document: {e}")
            raise e

    async def search(
            self,
            index_name: str,
            query: dict,
            params: Optional[Dict[str, Any]] = {},
            headers: Optional[Dict[str, Any]] = {}
    ) -> dict:
        try:
            response = await self.threading_util.run_in_thread(
                self.client.search,
                index=index_name,
                body=query,
                params=params,
                headers=headers
            )
            return response
        except OpenSearchException as e:
            logger.error(f"Error searching index: {e}")
            raise e

    async def get_document(
            self,
            index_name: str,
            document_id: str,
            params: Optional[Dict[str, Any]] = {},
            headers: Optional[Dict[str, Any]] = {}
    ) -> Optional[dict]:
        try:
            document = await self.threading_util.run_in_thread(
                self.client.get,
                index=index_name,
                id=document_id,
                params=params,
                headers=headers
            )

            if document is None:
                raise OpenSearchException(f"Document {document_id} not found.")

            return document
        except OpenSearchException as e:
            logger.error(f"Error getting document: {e}")
            raise e

    def close(self):
        self.client.close()


def get_opensearch_client() -> AsyncGenerator[OpenSearchClientInterface, None]:
    try:
        open_search_client = OpenSearchClient(
            threading_util=get_threading_util()
        )
        yield open_search_client
    except ConnectionError as e:
        logger.error(f"Error connecting to OpenSearch: {e}")
        raise e
    finally:
        open_search_client.close()
