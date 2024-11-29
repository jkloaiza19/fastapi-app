from fastapi import APIRouter
from api.v1.endpoints import AI
from api.v1.endpoints import user

v1_router = APIRouter()

v1_router.include_router(AI.router, prefix="/v1/ai", tags=["AI"])
v1_router.include_router(user.router, prefix="/v1/user", tags=["user"])
