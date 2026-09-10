from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from .config import get_settings


settings = get_settings()

def create_session_jwt(user_id: uuid.UUID | str) -> str:
    """
    mint a fresh session JWT for the given user id.

    Args:
        user_id: the User.id UUID (or its string from)

    Returns:
        A signed JWT string

    Notes:
        - TTL is governed by ACCESS_TOKEN_EXPIRE_MINUTES in settings.
        - The 'jti' (JWT ID) claim is a random UUID4 hex -- unique per token.
          We'll use this for denylisting in a future iteration.
    """

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": uuid.uuid4().hex,
        "iss": "DeployBridge",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_session_jwt(token: str) -> dict[str, Any]:
    """
    Verify and decode a session JWT.

    Raises jwt.PyJWTError (or a subclass) if:
      - signature is invalid (jwt.InvalidSignatureError)
      - token has expired (jwt.ExpiredSignatureError)
      - issuer is wrong (jwt.InvalidIssuerError)
      - algorithm differs from what we expect (prevents 'alg=none' attacks)
      - any required claim is missing

    Returns the decoded payload dict on success.
    """

    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        issuer="DeployBridge",
        options={"require": ["exp", "iat", "sub", "iss", "jti"]},
    )