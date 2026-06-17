from fastapi import APIRouter

from .v1.health import router as health_router


api_router = APIRouter(
    tags=["v1"],
    prefix='/v1',
)

api_router.include_router(health_router)