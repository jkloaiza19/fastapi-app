from functools import wraps
from fastapi import HTTPException, Request
from typing import Callable
from services.aws.cognito import CognitoClientInterface
from services.http.http_client import HttpClientInterface
from db.interfaces import DataBaseRepositoryInterface
from core.logger import get_logger

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

