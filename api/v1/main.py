from fastapi import APIRouter
from api.v1.endpoints import AI

v1_router = APIRouter()

v1_router.include_router(AI.router, prefix="/v1/ai", tags=["AI"])
