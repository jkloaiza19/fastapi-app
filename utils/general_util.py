from typing import Any


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
        raise TypeError(f"Unsupported response type for caching: {type(response)}")


def safe_serialize(obj: Any):
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)
