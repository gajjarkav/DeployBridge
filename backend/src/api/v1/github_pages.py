from fastapi import APIRouter,Header, HTTPException, status

from ...schemas.github_pages import (
    GitHubPagesDeployRequest,
    GitHubPagesDeployResponse,
)

from ...services.github_pages import GitHubPagesService
from ...core.exception import GitHubPagesError


router = APIRouter()

@router.post(
    '/deploy',
    response_model=GitHubPagesDeployResponse,
    summary="Deploy repository to GitHub Pages"
)
async def deploy_to_github_pages(
    request: GitHubPagesDeployRequest,
    authorization: str = Header(None),
):
    """Deploy a github repo to github pages"""

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )

    github_token = authorization.split(" ")[1]

    try:
        return await GitHubPagesService.deploy(
            github_token=github_token,
            owner=request.owner,
            repository=request.repository,
        )
    except GitHubPagesError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc
