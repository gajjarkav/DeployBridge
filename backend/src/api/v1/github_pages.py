from fastapi import APIRouter, Header, HTTPException, status

from ...core.exception import GitHubPagesError
from ...schemas.github_pages import (
    GitHubPagesDeployRequest,
    GitHubPagesDeployResponse,
    GitHubPagesDetectResponse,
    GitHubPagesRepositoryRequest,
)
from ...services.github_pages import GitHubPagesService


router = APIRouter()


def _extract_github_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )

    return authorization.split(" ", 1)[1]


@router.post(
    "/detect",
    response_model=GitHubPagesDetectResponse,
    summary="Detect GitHub Pages deployment profile",
)
async def detect_github_pages_profile(
    request: GitHubPagesRepositoryRequest,
    authorization: str | None = Header(None),
):
    github_token = _extract_github_token(authorization)

    try:
        return await GitHubPagesService.detect(
            github_token=github_token,
            owner=request.owner,
            repository=request.repository,
        )
    except GitHubPagesError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc


@router.post(
    "/deploy",
    response_model=GitHubPagesDeployResponse,
    summary="Deploy repository to GitHub Pages",
)
async def deploy_to_github_pages(
    request: GitHubPagesDeployRequest,
    authorization: str | None = Header(None),
):
    github_token = _extract_github_token(authorization)

    try:
        return await GitHubPagesService.deploy(
            github_token=github_token,
            owner=request.owner,
            repository=request.repository,
            deployment_profile=request.deployment_profile,
        )
    except GitHubPagesError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc
