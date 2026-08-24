import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...db.session import get_db
from ...models.user import User
from ...schemas.user import UserProfileResponse, UserDeployBranchUpdate
from ...services.github import GitHubService
from ...core.config import get_settings
from ...core.constants import const
from ...core.logger import logger


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


def _extract_bearer_token(authorization: str | None) -> str:
    """
    parse the "Authorization: Bearer <token>" header.
    returns the raw token string on success.
    raise 401 with a WWW-Authenticate response header (RFC 6750) on failure.
    """
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
            headers={"WWW-Authenticate": 'Bearer realm="DeployBridge'},
        )

    return authorization.split(" ", 1)[1]

def _hash_token_for_logging(token: str) -> str:
    """
    returna truncated SHA-256 hex digest of the token for safe logging.
    we log this on aith rejection so the team can correlate repeat offenders
    and detect brute-force patterns, Without leaking the raw token into
    log aggregators / dashboards / crash dumps.
    """

    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return digest[:12]

async def get_current_user_by_token(
    db: AsyncSession,
    authorization: str | None,
) -> User:
    """
    resolve the caller to a real user row from the database.
    contract:
        - the 'Authorization' header must be 'Bearer <toke>'
        - <token> must math a stored User.github_token in the database
        - otherwise: HTTP 401
    
    important: there is no fallback path. earlier versions fabricated a ghost User(github_id=0) for any token 
    longer than 5 chars, which let anonymous callers bypass authentication on every endpoint that depends on this function.
    that escape hatch has been removed deliberately
    """

    token = _extract_bearer_token(authorization)

    if len(token) < constant.MIN_TOKEN_LENGTH:
        logger.warning(
            "auth.rejected reason=too_short token_hash=%s len=%d",
            _hash_token_for_logging(token),
            len(token),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": 'Bearer realm="DeployBridge"'},
        )

    query = select(User).where(User.github_token == token)
    result = await db.execute(query)
    db_user = result.scalar_one_or_none()


    if db_user is None:
        logger.warning(
            "auth.rejected reason=no_match token_hash=%s",
            _hash_token_for_logging(token),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": 'Bearer realm="DeployBridge"'},
        )

    return db_user


@router.get("/profile", response_model=UserProfileResponse, summary="Get current user profile")
async def get_user_profile(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    db_user = await get_current_user_by_token(db, authorization)
    return UserProfileResponse.model_validate(db_user)


@router.patch("/profile", response_model=UserProfileResponse, summary="Update current user profile")
async def update_user_profile(
    payload: UserDeployBranchUpdate,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    db_user = await get_current_user_by_token(db, authorization)

    branch = payload.deploy_branch.strip() if payload.deploy_branch else None
    db_user.deploy_branch = branch or None

    await db.commit()
    await db.refresh(db_user)

    return UserProfileResponse.model_validate(db_user)
