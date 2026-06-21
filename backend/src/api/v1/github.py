import httpx
from fastapi import APIRouter, HTTPException, Header, status


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