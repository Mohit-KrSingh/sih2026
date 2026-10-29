"""TOTP MFA utilities for administrative roles."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pyotp

from app.auth.schemas import Role
from app.config import get_settings

MFA_ADMIN_ROLES: set[str] = {
    Role.AICTE_ADMIN.value,
    Role.AICTE_OFFICER.value,
    Role.COLLEGE_ADMIN.value,
}

MFA_PENDING_EXPIRE_MINUTES = 5


def role_requires_mfa(role: str) -> bool:
    """Check if a given user role mandates Multi-Factor Authentication."""
    return role in MFA_ADMIN_ROLES


def generate_totp_secret() -> str:
    """Generate a random Base32 TOTP secret key."""
    return pyotp.random_base32()


def get_totp_uri(
    secret: str,
    account_email: str,
    issuer_name: str = "AICTE APAAR",
) -> str:
    """Generate the standard otpauth:// URI for authenticator apps."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=account_email, issuer_name=issuer_name)


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    """Verify a 6-digit TOTP code against a Base32 secret.

    valid_window=1 permits 1 interval (30 seconds) of clock skew in either direction.
    """
    if not secret or not code:
        return False
    try:
        totp = pyotp.TOTP(secret)
        return bool(totp.verify(str(code).strip(), valid_window=valid_window))
    except Exception:
        return False


def create_mfa_pending_token(
    user_id: int,
    email: str,
    role: str,
    institution_id: int | None = None,
) -> str:
    """Create a short-lived intermediate JWT indicating password was verified but MFA is pending."""
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=MFA_PENDING_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "institution_id": institution_id,
        "type": "mfa_pending",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_mfa_pending_token(token: str) -> dict[str, Any]:
    """Decode and validate an MFA pending token."""
    settings = get_settings()
    decoded = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "iat", "sub", "type"]},
    )
    if decoded.get("type") != "mfa_pending":
        raise jwt.InvalidTokenError("Token is not an MFA pending token")
    return decoded
