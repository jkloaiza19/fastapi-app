from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from core.logger import get_logger
from api.dependencies import user_repository_dep
from schemas.user_schema import UserRequest
from typing import Dict
from api.dependencies import redis_dep

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def get_user(user_id: int, user_repository: user_repository_dep, redis: redis_dep):
    return await user_repository.find_unique(redis=redis, id=user_id)


@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=Dict)
async def create_user(user: UserRequest, user_repository: user_repository_dep, redis: redis_dep):
    logger.debug(f"user: {user.dict()}")
    return await user_repository.create_one(user)
