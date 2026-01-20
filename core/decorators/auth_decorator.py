from functools import wraps
from fastapi import HTTPException, Request
from typing import Callable, Optional
from services.aws.cognito import CognitoClientInterface
from services.http.http_client import HttpClientInterface
from db.interfaces import DataBaseRepositoryInterface
from core.logger import get_logger
from core.config import settings

logger = get_logger(__name__)


def token_required(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request: Request = kwargs.get("request")
        db: DataBaseRepositoryInterface = kwargs.get("db")
        aws_cognito_client: CognitoClientInterface = kwargs.get("aws_cognito_client")

        if not request:
            raise HTTPException(status_code=400, detail="Request object missing")

        token = request.headers.get("Authorization")

        if not token:
            raise HTTPException(status_code=401, detail="Authorization header missing")

        if token.startswith("Bearer "):
            token = token[len("Bearer "):]

        verified_user = await aws_cognito_client.verify_token(token, db)

        request.state.user = verified_user

        return await func(*args, **kwargs)

    return wrapper


def api_key_required(func: Callable):
    """
    Decorator to validate X-API-Key header for endpoint access.
    
    Usage:
        @router.post("/protected-endpoint")
        @api_key_required
        async def my_endpoint(request: Request):
            # Your endpoint logic
            pass
    
    The API key should be sent in the X-API-Key header.
    Configure valid keys in settings.API_KEYS (comma-separated string or list).
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request: Request = kwargs.get("request")

        if not request:
            raise HTTPException(status_code=400, detail="Request object missing")

        api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")

        if not api_key:
            logger.warning(f"API key missing for {request.url.path}")
            raise HTTPException(
                status_code=401, 
                detail="X-API-Key header required"
            )

        # Validate against configured API keys
        valid_keys = _get_valid_api_keys()
        
        if not valid_keys:
            logger.error("No API keys configured in settings")
            raise HTTPException(
                status_code=500, 
                detail="API authentication not configured"
            )

        if api_key not in valid_keys:
            logger.warning(f"Invalid API key attempt for {request.url.path}")
            raise HTTPException(
                status_code=403, 
                detail="Invalid API key"
            )

        logger.info(f"Valid API key access to {request.url.path}")
        return await func(*args, **kwargs)

    return wrapper


def _get_valid_api_keys() -> set:
    """
    Get valid API keys from settings.
    Supports both comma-separated string or list format.
    """
    api_keys = getattr(settings, "API_KEYS", None)
    
    if not api_keys:
        return set()
    
    if isinstance(api_keys, str):
        # Split comma-separated string and strip whitespace
        return set(key.strip() for key in api_keys.split(",") if key.strip())
    
    if isinstance(api_keys, list):
        return set(api_keys)
    
    return set()

