from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...db.session import get_db
from ...models.user import User
from ...services.github import GitHubService
from ...core.config import get_settings


settings = get_settings()

router = APIRouter()


@router.get('/login', summary="Get Github Login URL")
async def get_github_login_url():
    """
    the frontend calls this to get the official GitHub autorization URL,
    the frontend should then redirect the user to this URL
    """

    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&scope=read:user%20user:email%20repo%20workflow"
    )

    return {
        "login_url": url
    }


@router.get('/callback', summary="Handle GitHub Callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    """
    GitHub redirects backto the frontend with a 'code',
    the frontend sends that code here to compelete the login.
    """

    token_data = await GitHubService.get_access_token(code)

    github_user = await GitHubService.get_user_profile(token_data["access_token"])

    print("TOKEN SCOPES:", token_data["scope"])

    query = select(User).where(User.github_id == github_user["github_id"])
    result = await db.execute(query)
    db_user = result.scalar_one_or_none()


    if not db_user:
        db_user = User(
            github_id=github_user["github_id"],
            username=github_user["username"],
            email=github_user["email"],
            avatar_url=github_user["avatar_url"],
            github_token=token_data["access_token"],
            github_token_type=token_data["token_type"],
            github_scope=token_data["scope"],
            last_login=datetime.now(timezone.utc),
        )
        db.add(db_user)
    else:
        db_user.username = github_user["username"]
        db_user.email = github_user["email"]
        db_user.avatar_url = github_user["avatar_url"]
        db_user.github_token = token_data["access_token"]
        db_user.github_token_type = token_data["token_type"]
        db_user.github_scope = token_data["scope"]
        db_user.last_login = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_user)

    return {
        "message": "Login successful",
        "user": {
            "id": str(db_user.github_id),
            "username": db_user.username,
            "email": db_user.email,
            "avatar_url": db_user.avatar_url,
            "last_login": db_user.last_login.isoformat(),
            "scope": db_user.github_scope,
            "token_type": db_user.github_token_type,
        },
        "github_access_token": token_data["access_token"],
        "scope": db_user.github_scope,
        "token_type": db_user.github_token_type,
        "last_login": db_user.last_login.isoformat(),
    }
