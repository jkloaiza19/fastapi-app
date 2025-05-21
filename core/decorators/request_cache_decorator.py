import functools
import hashlib
import json
import inspect
from fastapi import Request
from typing import Callable, Optional, Any
from services.redis.redis_client import redis_dep
from utils.general_util import safe_serialize, serialize_response


def request_cache_response(ttl: int = 300,):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, request: Optional[Request] = None, redis_client: redis_dep, **kwargs):
            filtered_kwargs = {
                k: safe_serialize(v)
                for k, v in kwargs.items()
                if isinstance(v, (str, int, float, bool, type(None)))
            }
            key_input = {
                "path": str(request.url.path) if request else func.__name__,
                "query": str(request.url.query) if request else "",
                "kwargs": filtered_kwargs,
            }
            cache_key = f"cache:{hashlib.sha256(json.dumps(key_input, sort_keys=True).encode()).hexdigest()}"

            cached = await redis_client.get_cached_data(cache_key)
            print("Cached data:", cached)
            if cached:
                return cached

            sig = inspect.signature(func)
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()

            response = await func(*bound_args.args, redis_client, **bound_args.kwargs)

            info_to_cache = serialize_response(response)

            await redis_client.set_cache_data(
                cache_key, {
                    **info_to_cache,
                    **({"created_at": str(info_to_cache["created_at"])} if "created_at" in info_to_cache else {}),
                    **({"updated_at": str(info_to_cache["updated_at"])} if "updated_at" in info_to_cache else {})
                }
            )
            return response
        return wrapper
    return decorator
