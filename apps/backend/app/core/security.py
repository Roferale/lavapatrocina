from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing (bcrypt)
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the bcrypt *hashed* password."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create and return a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode a JWT token and return the payload, or None if invalid/expired."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Field-level encryption (Fernet / AES-128-CBC)
# ---------------------------------------------------------------------------

def _fernet() -> Fernet:
    """Build a Fernet instance from the 32-char ENCRYPTION_KEY.

    The key must be exactly 32 ASCII chars.  We base64url-encode those 32 bytes
    to produce the 44-character token that Fernet expects.  This is identical to
    the approach used by the worker so that encrypted values round-trip correctly.
    """
    raw = settings.ENCRYPTION_KEY.encode("ascii")
    if len(raw) != 32:
        raise ValueError(
            f"ENCRYPTION_KEY must be exactly 32 ASCII chars, got {len(raw)}"
        )
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt_text(text: str) -> str:
    """Encrypt *text* and return a URL-safe base64 token."""
    return _fernet().encrypt(text.encode()).decode()


def decrypt_text(encrypted: str) -> str:
    """Decrypt a token produced by :func:`encrypt_text`."""
    return _fernet().decrypt(encrypted.encode()).decode()
