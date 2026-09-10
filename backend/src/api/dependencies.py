from __future__ import annotations

import hashlib
import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logger import logger
from ..core.security import decode_session_jwt
from ..db.session import get_db
from ..models.user import User

from ..core.constants import const


constant = const()

def _extract_bearer_token(authorization: str | None) -> str:
    """
    Parse 'Authorization: Bearer <token>' and return the token.
    Raises 401 with RFC-6750 WWW-Authenticate header on failure.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
            headers={"WWW-Authenticate": 'Bearer realm="DeployBridge"'},
        )
    return authorization.split(" ", 1)[1]


def _hash_token_for_logging(token: str) -> str:
    """Truncated SHA-256 hex of a token -- safe to log without leaking the secret."""
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return digest[:12]


async def _resolve_via_jwt(token: str, db: AsyncSession) -> User | None:
    """
    authenticate the token as a session

    Returns the User row on success, or None if the token is not a valid
    JWT at all (malformed / bad signature / expired) -- in which case the
    caller rejects the request, since there is no fallback anymore.

    Raises HTTPException(401) if the JWT is well-formed but references
    a user that doesn't exist -- that's a real auth failure, not a
    fallback signal.
    """
    try:
        payload = decode_session_jwt(token)
    except Exception as exc:
        logger.debug(
            "auth.jwt_verification_failed error_type=%s token_hash=%s",
            type(exc).__name__,
            _hash_token_for_logging(token),
        )
        return None

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        logger.warning(
            "auth.rejected reason=malformed_jwt_sub payload_sub=%r",
            payload.get("sub"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": 'Bearer realm="DeployBridge"'},
        )

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    db_user = result.scalar_one_or_none()

    if db_user is None:
        logger.warning(
            "auth.rejected reason=user_not_found user_id=%s",
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": 'Bearer realm="DeployBridge"'},
        )

    return db_user

async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency. Resolves the caller to a User row.

    Raises HTTPException(401) on any failure.
    """
    token = _extract_bearer_token(authorization)

    user = await _resolve_via_jwt(token, db)
    if user is not None:
        return user

    logger.warning(
        "auth.rejected reson=invalid_or_epired_jwt token_hash=%s",
        _hash_token_for_logging(token),
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session token.",
        headers={"WWW-Authenticate": 'Bearer realm="DeployBridge"'},
    )
