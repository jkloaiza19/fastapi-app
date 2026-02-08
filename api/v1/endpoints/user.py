from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse
from core.logger import get_logger
# from api.dependencies import user_repository_dep
from schemas.user_schema import UserRequest, UserResponse
from typing import Dict
from api.dependencies import redis_dep
from core.decorators.request_cache_decorator import request_cache_response
from utils.pagination_util import get_base_url
from db.database_repository import user_repository_dep

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
    description="""Retrieve a specific user's profile by their user ID.
    
    **Features:**
    - Response cached for 5 minutes (300 seconds)
    - Returns complete user profile
    
    **Returns:**
    - User ID, username, and email
    - Account confirmation status
    - Created and updated timestamps
    """,
    response_model=UserResponse,
    responses={
        200: {"description": "User found and returned"},
        404: {"description": "User not found"}
    }
)
@request_cache_response(ttl=300)
async def get_user(user_id: int, user_repository: user_repository_dep, redis_client: redis_dep):
    user = await user_repository.find_unique(redis=None, id=user_id)
    if user is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": "User not found"})

    # Handle both User object and dict from cache
    if isinstance(user, dict):
        return UserResponse(**user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_confirmed=user.is_confirmed,
        created_at=str(user.created_at),
        updated_at=str(user.updated_at)
    )


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    response_model=Dict,
    summary="Create a new user",
    description="""Create a new user record in the database.
    
    **Note:** This is a direct database operation. For standard user registration
    with email confirmation, use the `/auth/register` endpoint instead.
    
    **Required fields:**
    - username: Unique username
    - email: Valid email address
    - password: User password
    """,
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid user data or duplicate username/email"},
        500: {"description": "Database error"}
    }
)
async def create_user(user: UserRequest, user_repository: user_repository_dep, redis: redis_dep):
    logger.debug(f"user: {user.dict()}")
    return await user_repository.create_one(user)
