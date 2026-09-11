from fastapi import APIRouter, HTTPException, Depends, Header, status

from ...core.exception import GitHubAPIError
from ...models.user import User
from ...schemas.repo_info import RepositoryInfoResponse, RepositoryInfoRequest
from ...services.github import GitHubService
from ..dependencies import get_current_user
from ...core.crypto import TokenDecryptionError, decrypt_secret


router = APIRouter()


@router.post(
    '/repos/info',
    response_model=RepositoryInfoResponse,
    summary="Fetch comprehensive repository information",
)
async def get_repository_info(
    request: RepositoryInfoRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Fetches detailed information about a specific repository

    Returns comprehensive data including:
    - Basic repository metadata (stars, forks, description, etc.)
    - Deployment status (GitHub Pages, other platforms)
    - Language breakdown with percentages
    - Detected tech stack
    - Recent commit history
    - Contributors list
    - Branches information
    - README content
    - Root file tree
    
    All data is fetched in parallel for optimal performance.
    Supports both public and private repositories (with proper OAuth scope)
    """

    if not current_user.github_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your GitHub access token is missing from our records, please re-authenticate",
        )

    try:
        github_token = decrypt_secret(current_user.github_token)

        result = await GitHubService.get_repository_info(
            token=github_token,
            owner=request.owner,
            repo=request.repository,
        )

        return result

    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    except GitHubAPIError as exc:
        raise HTTPException(
            status_code=exc.status_code if hasattr(exc, "status_code") else 502,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch repository information: {str(exc)}",
        ) from exc