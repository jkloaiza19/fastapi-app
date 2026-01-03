from typing import Any
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.logger import get_logger
from core.config import settings

logger = get_logger(__name__)


def serialize_response(response):
    if hasattr(response, "model_dump"):  # Pydantic v2
        return response.model_dump()
    elif hasattr(response, "dict"):  # Pydantic v1
        return response.dict()
    elif hasattr(response, "to_dict"):  # Custom method
        return response.to_dict()
    elif isinstance(response, (dict, list, str, int, float, bool, type(None))):
        return response
    else:
        logger.error(f"Unsupported response type for caching: {type(response)}")
        raise TypeError(f"Unsupported response type for caching: {type(response)}")


def safe_serialize(obj: Any):
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


def get_limiter() -> Limiter:
    """
    Get the global rate limiter instance.
    """
    limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)

    return limiter
