from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception import GitHubPagesError
from ...models.user import User
from ...schemas.github_pages import (
    GitHubPagesDeployRequest,
    GitHubPagesDeployResponse,
    GitHubPagesDetectResponse,
    GitHubPagesRepositoryRequest,
)
from ...services.github_pages import GitHubPagesService
from ..dependencies import get_current_user
from ...core.crypto import TokenDecryptionError, decrypt_secret


router = APIRouter()


@router.post(
    "/detect",
    response_model=GitHubPagesDetectResponse,
    summary="Detect GitHub Pages deployment profile",
)
async def detect_github_pages_profile(
    request: GitHubPagesRepositoryRequest,
    current_user: User = Depends(get_current_user)
):
    if not current_user.github_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your GitHub access token is missing from our records. Please re-authenticate.",
        )

    try:
        github_token = decrypt_secret(current_user.github_token)
        return await GitHubPagesService.detect(
            github_token=github_token,
            owner=request.owner,
            repository=request.repository,
            preferred_branch=current_user.deploy_branch,
        )
    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
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
    current_user: User = Depends(get_current_user)
):
    if not current_user.github_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your GitHub access token is missing from our records. Please re-authenticate.")

    try:
        github_token = decrypt_secret(current_user.github_token)
        return await GitHubPagesService.deploy(
            github_token=github_token,
            owner=request.owner,
            repository=request.repository,
            deployment_profile=request.deployment_profile,
            preferred_branch=current_user.deploy_branch,
        )
    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except GitHubPagesError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc
