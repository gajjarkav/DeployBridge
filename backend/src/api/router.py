from fastapi import APIRouter

from .v1.health import router as health_router
from .v1.auth import router as auth_router
from .v1.github import router as github_router


api_router = APIRouter(
    tags=["v1"],
    prefix='/v1',
)

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router, prefix='/auth', tags=["Authentication"])
api_router.include_router(github_router, prefix='/github', tags=["GitHub Data"])