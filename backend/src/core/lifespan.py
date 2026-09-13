import logging

from .config import get_settings


settings = get_settings()

logger = logging.getLogger(settings.APP_NAME)


async def _encrypt_existing_github_tokens() -> int:
    """
    One-time (per boot) migration for Item 2: encrypt any
    users.github_token rows that are still plaintext.

    When does a plaintext row exist?
      - Rows written before Item 2 shipped (i.e. today's existing users).
      - Rows restored from an old backup or inserted by hand.

    How it decides: `is_encrypted()` checks the Fernet version-byte
    prefix ("gAAAA"). GitHub tokens start with gho_/ghp_/... and can
    never produce that prefix, so the check cannot false-positive.

    Idempotency: rows already encrypted are skipped, so re-running the
    boot (uvicorn --reload restarts, container redeployments) is free.
    The migration never DECRYPTS anything -- it only ever wraps
    plaintext -- so a wrong key cannot corrupt rows here.

    Multi-worker caveat: if several workers boot simultaneously they
    may race on the same plaintext row. Worst case both encrypt and one
    write wins -- the stored value is still valid ciphertext, so the
    outcome is safe. For large tables, promote this to a one-off
    Alembic data migration instead.
    """

    from sqlalchemy import select

    from ..db.session import AsyncSessionLocal
    from ..models.user import User
    from .crypto import encrypt_secret, is_encrypted

    encrypted_count = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.github_token.is_not(None))
        )
        users = result.scalars().all()

        for user in users:
            if not is_encrypted(user.github_token):
                user.github_token = encrypt_secret(user.github_token)
                encrypted_count += 1

            if encrypted_count:
                await session.commit()

    return encrypted_count


async def lifespan(app):
    """
    FastAPI lifespan runs on startup and shutdown
    """
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} starting...")
    logger.info(f"Debug mode: {settings.DEBUG}")

    from .crypto import get_fernet

    get_fernet()

    encrypted_count = await _encrypt_existing_github_tokens()
    logger.info(
        "crypto.token_encryption_migration encrypted_rows=%d", encrypted_count
    )

    from ..services.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    yield

    stop_scheduler()
    logger.info("Shutting down...")