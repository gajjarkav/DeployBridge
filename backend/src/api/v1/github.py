import httpx
from fastapi import APIRouter, HTTPException ,Depends , Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception import GitHubAPIError
from ...db.session import get_db
from ...schemas.repo_info import RepositoryInfoResponse, RepositoryInfoRequest
from ...services.github import GitHubService
from .auth import get_current_user_by_token


router = APIRouter()

@router.get('/repos', summary="fetch and format user repositories")
async def get_user_repositories(authorization: str = Header(None)):
    """
    expects a github access token in the authorization header,
    fetcheds repos from github and formats them for the frontend table.
    """

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid Authorization header",
        )

    token = authorization.split(" ")[1]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.github.com/user/repos?sortupdated&per_page=10", headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch repos from GitHub"
            )
        
        github_repos = response.json()

    formatted_repos = []
    for index, repo in enumerate(github_repos, start=1):
        formatted_repos.append({
            "index": index,
            "id": repo["id"],
            "name": repo["name"],
            "url": repo["html_url"],
            "language": repo.get("language") or "N/A",
            "visibility": repo["visibility"].capitalize(),
            "status": "Ready to Scan"
        })

    return formatted_repos


@router.post(
    '/repos/info',
    response_model=RepositoryInfoResponse,
    summary="Fetch comprehensive repository information",
)
async def get_repository_info(
    request: RepositoryInfoRequest,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
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

    db_user = await get_current_user_by_token(db, authorization)
    if not db_user or not db_user.github_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing GitHub access token, please authenticate first",
        )

    try:
        result = await GitHubService.get_repository_info(
            token=db_user.github_token,
            owner=request.owner,
            repo=request.repository,
        )

        return result

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