import hashlib

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...db.session import get_db
from ...models.user import User
from ...schemas.user import UserProfileResponse, UserDeployBranchUpdate
from ...services.github import GitHubService
from ...core.config import get_settings
from ...core.constants import const
from ...core.security import create_session_jwt
from ..dependencies import get_current_user
from ...core.crypto import encrypt_secret


settings = get_settings()
constant = const()

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
            github_token=encrypt_secret(token_data["access_token"]),
            github_token_type=token_data["token_type"],
            github_scope=token_data["scope"],
            last_login=datetime.now(timezone.utc),
        )
        db.add(db_user)
    else:
        db_user.username = github_user["username"]
        db_user.email = github_user["email"]
        db_user.avatar_url = github_user["avatar_url"]
        db_user.github_token = encrypt_secret(token_data["access_token"])
        db_user.github_token_type = token_data["token_type"]
        db_user.github_scope = token_data["scope"]
        db_user.last_login = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_user)

    session_token = create_session_jwt(db_user.id)

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
        "session_token": session_token,
        "github_access_token": token_data["access_token"],
        "scope": db_user.github_scope,
        "token_type": db_user.github_token_type,
        "last_login": db_user.last_login.isoformat(),
    }



@router.get("/profile", response_model=UserProfileResponse, summary="Get current user profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    returns the profile of the authenticated caller
    
    Auth is handled by the `get_current_user` dependency, which accepts
    ONLY session JWTs -- the legacy raw-github-token fallback was removed
    in Item 3c once the frontend stopped sending raw GitHub tokens.
    """
    return UserProfileResponse.model_validate(current_user)


@router.patch("/profile", response_model=UserProfileResponse, summary="Update current user profile")
async def update_user_profile(
    payload: UserDeployBranchUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates the deploy branch preference for the authenticated caller.
    
    Note: we need `db` here because we're modifying the user row. The
    `get_current_user` dependency already loaded the user via the same
    session, so the same session is reused (FastAPI caches dependency
    results within a single request).
    """

    branch = payload.deploy_branch.strip() if payload.deploy_branch else None
    
    current_user.deploy_branch = branch or None

    await db.commit()
    await db.refresh(current_user)

    return UserProfileResponse.model_validate(current_user)


@router.post('/refresh', summary="Refresh session token")
async def refresh_session(
    current_user: User = Depends(get_current_user),
):
    """
    Exchange a valid (non-expired) session JWT for a fresh one.
    
    Used by the frontend to keep the user logged in without forcing
    re-authentication through GitHub. The frontend should call this
    endpoint shortly before the current JWT expires.
    
    Returns a new `session_token` field. The old token remains valid
    until its own `exp` -- in a future iteration we will denylist the
    old `jti` on refresh (token rotation).
    """

    new_token = create_session_jwt(current_user.id)

    return {"session_token": new_token}


@router.post('/logout', summary="Logout")
async def logout(
    authorization: str | None = Header(None),
):
    """
    Mark the current session as ended.
    
    In Item 3a this is effectively a no-op: we don't have a token denylist
    yet, so the JWT remains valid until its `exp` expires. We return 200
    so the frontend can call this on user-initiated logout (the frontend
    will also clear its localStorage).
    
    TODO (Item 7): add the JWT's `jti` to a `revoked_tokens` table on
    logout, and have `get_current_user` check that table.
    """

    return {
        "message": "Logged out"
    }