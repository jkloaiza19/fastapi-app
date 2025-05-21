from fastapi import APIRouter
from api.v1.endpoints import AI
from api.v1.endpoints import user
from api.v1.endpoints import auth
from api.v1.endpoints import notifications

v1_router = APIRouter()

v1_router.include_router(AI.router, prefix="/v1/ai", tags=["AI"])
v1_router.include_router(user.router, prefix="/v1/user", tags=["user"])
v1_router.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
v1_router.include_router(notifications.router, prefix="/v1/notifications", tags=["notifications"])
