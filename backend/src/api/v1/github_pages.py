from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception import GitHubPagesError
from ...db.session import get_db
from ...schemas.github_pages import (
    GitHubPagesDeployRequest,
    GitHubPagesDeployResponse,
    GitHubPagesDetectResponse,
    GitHubPagesRepositoryRequest,
)
from ...services.github_pages import GitHubPagesService
from .auth import get_current_user_by_token


router = APIRouter()


@router.post(
    "/detect",
    response_model=GitHubPagesDetectResponse,
    summary="Detect GitHub Pages deployment profile",
)
async def detect_github_pages_profile(
    request: GitHubPagesRepositoryRequest,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    db_user = await get_current_user_by_token(db, authorization)
    github_token = db_user.github_token

    if not github_token:
        raise HTTPException(status_code=401, detail="Missing GitHub access token.")

    try:
        return await GitHubPagesService.detect(
            github_token=github_token,
            owner=request.owner,
            repository=request.repository,
            preferred_branch=db_user.deploy_branch,
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
    db: AsyncSession = Depends(get_db),
):
    db_user = await get_current_user_by_token(db, authorization)
    github_token = db_user.github_token

    if not github_token:
        raise HTTPException(status_code=401, detail="Missing GitHub access token.")

    try:
        return await GitHubPagesService.deploy(
            github_token=github_token,
            owner=request.owner,
            repository=request.repository,
            deployment_profile=request.deployment_profile,
            preferred_branch=db_user.deploy_branch,
        )
    except GitHubPagesError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc
