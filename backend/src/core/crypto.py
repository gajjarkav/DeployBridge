from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings
from .constants import const
from .logger import logger


settings = get_settings()
constant = const()


class TokenDecryptionError(RuntimeError):
    """
    Raised when a stored value LOOKS like Fernet ciphertext but fails to
    decrypt. That means one of exactly two things:

      1. The GITHUB_TOKEN_ENCRYPTION_KEY was changed/rotated without
         re-encrypting the stored rows, or
      2. The ciphertext was tampered with in the database.

    Both are server-side faults, not user faults -- callers should
    surface a 500 and an operator should look at the logs. The remedy
    for end users is the same either way: log in again, which stores a
    fresh token encrypted under the current key.
    """


@lru_cache
def get_fernet() -> Fernet:
    """
    Build (and cache) the Fernet instance from settings.

    lru_cache: Fernet(key) validates and decodes the key; doing that on
    every encrypt/decrypt call would be wasted work for a value that
    never changes at runtime. First call doubles as the startup key
    validation -- lifespan calls this eagerly so a malformed key fails
    the boot, not the first user request.
    """
    key = get_settings().GITHUB_TOKEN_ENCRYPTION_KEY
    # Fernet() raises ValueError if the key is not 32 url-safe
    # base64-encoded bytes. We re-raise with an actionable message
    # because "invalid base64" alone does not tell the operator what
    # env var to fix.
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise RuntimeError(
            "GITHUB_TOKEN_ENCRYPTION_KEY is missing or malformed. "
            "Generate one with: "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())" '
            "and set it in backend/.env"
        ) from exc


def is_encrypted(value: str | None) -> bool:
    """
    True if the value looks like Fernet ciphertext (starts with the
    version-byte prefix). Used by the startup migration to decide which
    rows still need encrypting -- GitHub tokens can never produce this
    prefix, so there are no false positives in practice.
    """
    return bool(value) and value.startswith(constant.FERNET_TOKEN_PREFIX)


def encrypt_secret(plaintext: str | None) -> str | None:
    """
    Encrypt a secret for storage. Returns a base64url Fernet token.

    None/empty pass through unchanged so callers can write
    `encrypt_secret(maybe_none_value)` without a guard -- encrypting an
    empty string would be pointless (and would mask "no token" in the
    400-checks the endpoints already do on falsiness).
    """
    if not plaintext:
        return plaintext
    # .decode(): Fernet.encrypt returns bytes; the DB column is String.
    return get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    """
    Decrypt a stored secret back to plaintext (in memory only).

    Three cases, in order:
      1. None/empty        -> pass through (nothing to decrypt).
      2. Plaintext value   -> pass through WITH a WARNING log. After the
         startup migration this should never happen; if it does, someone
         inserted/restored a row outside the app. The warning makes the
         gap visible in ops instead of failing silently.
      3. Fernet ciphertext -> decrypt and verify the HMAC. Failure means
         key mismatch or tampering: raise TokenDecryptionError (caller
         turns it into a 500; the user can fix it by re-logging in).
    """
    if not value:
        return value

    if not is_encrypted(value):
        logger.warning(
            "crypto.plaintext_row_detected note=row_stored_without_encryption "
            "value_prefix=%s... len=%d",
            value[:4],
            len(value),
        )
        return value

    try:
        return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        # Log WITHOUT the value: even truncated, ciphertext + this error
        # is a forensic clue we want in logs; the plaintext never is.
        logger.error(
            "crypto.decrypt_failed reason=hmac_or_key_mismatch len=%d",
            len(value),
        )
        raise TokenDecryptionError(
            "Failed to decrypt a stored secret: the encryption key does "
            "not match this data, or the data was tampered with. The user "
            "should re-authenticate."
        ) from exc
