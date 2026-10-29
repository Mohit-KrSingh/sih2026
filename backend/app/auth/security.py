"""Authentication security utilities: Argon2 password hashing and JWT management."""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2 hash.

    Returns True if valid, False if mismatch or corrupted hash.
    """
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:
        return False


def create_access_token(
    user_id: int,
    email: str,
    role: str,
    institution_id: int | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "institution_id": institution_id,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: int,
    email: str,
    role: str,
    institution_id: int | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT refresh token."""
    settings = get_settings()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "institution_id": institution_id,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.PyJWTError: Invalid signature, malformed token, or decode error.
    """
    settings = get_settings()
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "iat", "sub", "type"]},
    )


def create_password_reset_token(
    user_id: int,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT password reset token."""
    settings = get_settings()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=15)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "type": "password_reset",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_password_reset_token(token: str) -> dict[str, Any]:
    """Decode and validate a password reset JWT token."""
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "iat", "sub", "type"]},
    )
    if payload.get("type") != "password_reset":
        raise jwt.InvalidTokenError("Invalid token type: expected password_reset")
    return payload


def get_fernet() -> Fernet:
    """Get Fernet cipher instance from application settings."""
    settings = get_settings()
    return Fernet(settings.FERNET_KEY.encode())


def encrypt_dob(d: date | str) -> str:
    """Encrypt date of birth using application Fernet key per SPEC.md Section 16."""
    val = d.isoformat() if isinstance(d, date) else str(d)
    return get_fernet().encrypt(val.encode()).decode()


def decrypt_dob(encrypted: str) -> date:
    """Decrypt date of birth using application Fernet key."""
    try:
        val = get_fernet().decrypt(encrypted.encode()).decode()
        return date.fromisoformat(val)
    except (InvalidToken, Exception):
        # Fallback for plain ISO strings (useful for mock/test data)
        try:
            return date.fromisoformat(encrypted)
        except Exception as e:
            raise ValueError(f"Cannot decrypt date of birth: {encrypted}") from e
