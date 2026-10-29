"""Redis-backed One-Time Password (OTP) service."""

import hmac
import json
import secrets
from typing import Any

import redis
from sqlalchemy.orm import Session

from app.integrations.factory import get_otp_sender

OTP_EXPIRY_SECONDS = 300  # 5 minutes
MAX_ATTEMPTS = 5


def generate_numeric_otp(length: int = 6) -> str:
    """Generate a cryptographically secure random numeric OTP."""
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def _make_otp_key(purpose: str, recipient: str) -> str:
    """Construct standard Redis key for OTP storage."""
    clean_purpose = purpose.strip().lower()
    clean_recipient = recipient.strip().lower()
    return f"otp:{clean_purpose}:{clean_recipient}"


def store_and_send_otp(
    db: Session,
    redis_client: redis.Redis,
    recipient: str,
    channel: str = "email",
    purpose: str = "general",
    context: str = "",
    code_length: int = 6,
) -> dict[str, Any]:
    """Generate, store in Redis with 5-minute TTL, and dispatch via OtpSender.

    Returns metadata dictionary including recipient, channel, purpose, and expiry.
    """
    code = generate_numeric_otp(length=code_length)
    key = _make_otp_key(purpose, recipient)

    payload = {
        "code": code,
        "attempts": 0,
        "max_attempts": MAX_ATTEMPTS,
        "channel": channel,
        "recipient": recipient.strip().lower(),
        "purpose": purpose.strip().lower(),
    }

    # Store in Redis with 5-minute expiry
    redis_client.set(key, json.dumps(payload), ex=OTP_EXPIRY_SECONDS)

    # Dispatch via OtpSender interface
    sender = get_otp_sender(db)
    sender.send_otp(channel=channel, recipient=recipient, code=code, context=context)
    db.commit()

    return {
        "status": "sent",
        "recipient": recipient,
        "channel": channel,
        "purpose": purpose,
        "expires_in": OTP_EXPIRY_SECONDS,
        "message": f"OTP successfully sent via {channel}.",
    }


def verify_otp(
    redis_client: redis.Redis,
    recipient: str,
    purpose: str,
    code: str,
) -> tuple[bool, str, int]:
    """Verify an OTP code against Redis storage.

    Returns:
        (success: bool, message: str, remaining_attempts: int)

    Behavior:
        - If expired or not found: returns (False, error_msg, 0)
        - If attempts >= 5: invalidates OTP and returns (False, lockout_msg, 0)
        - If matched: deletes key from Redis and returns (True, success_msg, 0)
        - If mismatched: increments attempts, updates TTL, returns (False, attempt_msg, remaining)
    """
    key = _make_otp_key(purpose, recipient)
    raw_data = redis_client.get(key)

    if raw_data is None:
        return False, "OTP has expired or was not requested. Please request a new code.", 0

    try:
        data = json.loads(raw_data)
    except Exception:
        redis_client.delete(key)
        return False, "Corrupted OTP session. Please request a new code.", 0

    attempts = int(data.get("attempts", 0))
    max_attempts = int(data.get("max_attempts", MAX_ATTEMPTS))

    # Lockout check: if already at or exceeded max attempts
    if attempts >= max_attempts:
        redis_client.delete(key)
        return (
            False,
            (
                "Maximum verification attempts exceeded. "
                "OTP has been invalidated. Please request a new code."
            ),
            0,
        )

    expected_code = str(data.get("code", ""))
    candidate_code = str(code).strip()

    # Constant-time comparison
    if hmac.compare_digest(expected_code, candidate_code):
        # Successful verification: delete OTP immediately to prevent replay
        redis_client.delete(key)
        return True, "OTP verified successfully.", 0

    # Incorrect code: increment attempts counter while preserving remaining TTL
    new_attempts = attempts + 1
    data["attempts"] = new_attempts
    remaining_attempts = max(0, max_attempts - new_attempts)

    if remaining_attempts <= 0:
        redis_client.delete(key)
        return (
            False,
            (
                "Maximum verification attempts exceeded. "
                "OTP has been invalidated. Please request a new code."
            ),
            0,
        )

    # Update attempt count with remaining TTL
    ttl = redis_client.ttl(key)
    if ttl > 0:
        redis_client.set(key, json.dumps(data), ex=ttl)
    else:
        redis_client.delete(key)
        return False, "OTP has expired. Please request a new code.", 0

    return (
        False,
        f"Invalid OTP code. {remaining_attempts} attempt(s) remaining.",
        remaining_attempts,
    )


def invalidate_otp(redis_client: redis.Redis, recipient: str, purpose: str) -> bool:
    """Manually invalidate an active OTP in Redis."""
    key = _make_otp_key(purpose, recipient)
    return bool(redis_client.delete(key))
