"""Tests for OTP, TOTP MFA, and Rate Limiting.

SPEC.md section 11, 14, 16, TASKS.md T05:
- OTP in Redis with 5-minute expiry and 5 attempts.
- TOTP for admin roles.
- Rate limits on login, OTP, and verify endpoints.
- Tests for expiry, attempt lockout, and rate limit responses (429 + Retry-After).
"""

import json
import time

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.otp import (
    OTP_EXPIRY_SECONDS,
    _make_otp_key,
    store_and_send_otp,
    verify_otp,
)
from app.auth.rate_limiter import reset_rate_limit
from app.auth.security import create_access_token, hash_password
from app.auth.totp import (
    generate_totp_secret,
    get_totp_uri,
    role_requires_mfa,
    verify_totp,
)
from app.config import get_settings
from app.db import get_redis_client
from app.models import DevOutbox, Institution, User

settings = get_settings()


@pytest.fixture
def redis_conn():
    """Direct Redis client connection for test verification."""
    client = get_redis_client()
    yield client
    client.close()


def _create_institution_and_user(
    db: Session,
    role: str = "college_admin",
    mfa_secret: str | None = None,
) -> tuple[Institution, User, str]:
    """Helper to create a test institution and user."""
    unique_suffix = f"{int(time.time() * 1000)}"
    inst = Institution(
        aicte_id=f"TEST-OTP-{unique_suffix}",
        name=f"Test Institute {unique_suffix}",
        state="Maharashtra",
        district="Pune",
        address="123 Academic Way",
        official_email=f"inst_{unique_suffix}@example.edu",
        official_phone="+919876543210",
        head_name="Dr. Registrar",
        affiliating_university="State Tech University",
        approval_status="active",
        account_status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)

    raw_password = "Password@12345"
    user = User(
        email=f"admin_{unique_suffix}@example.edu",
        password_hash=hash_password(raw_password),
        role=role,
        institution_id=inst.id,
        mfa_secret=mfa_secret,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return inst, user, raw_password


# =============================================================================
# 1. OTP In Redis Tests (5-minute expiry, 5 attempts, lockout)
# =============================================================================


def test_otp_generation_storage_and_ttl(db_session: Session, redis_conn):
    """Test OTP creation, storage in Redis with 5-minute expiry, and dev_outbox dispatch."""
    recipient = f"verify_{int(time.time())}@example.edu"
    purpose = "activation"

    result = store_and_send_otp(
        db=db_session,
        redis_client=redis_conn,
        recipient=recipient,
        channel="email",
        purpose=purpose,
        context="College activation claim",
    )

    assert result["status"] == "sent"
    assert result["recipient"] == recipient
    assert result["expires_in"] == OTP_EXPIRY_SECONDS

    # Verify Redis key and TTL (around 300s)
    key = _make_otp_key(purpose, recipient)
    raw_data = redis_conn.get(key)
    assert raw_data is not None

    data = json.loads(raw_data)
    assert len(data["code"]) == 6
    assert data["code"].isdigit()
    assert data["attempts"] == 0
    assert data["max_attempts"] == 5

    ttl = redis_conn.ttl(key)
    assert 280 <= ttl <= 300

    # Verify message in dev_outbox
    outbox_msg = db_session.scalar(
        select(DevOutbox).where(DevOutbox.recipient == recipient).order_by(DevOutbox.id.desc())
    )
    assert outbox_msg is not None
    assert data["code"] in outbox_msg.body


def test_otp_successful_verification_deletes_key(db_session: Session, redis_conn):
    """Test successful OTP verification deletes the Redis key to prevent replay."""
    recipient = f"success_{int(time.time())}@example.edu"
    purpose = "login"

    store_and_send_otp(
        db=db_session,
        redis_client=redis_conn,
        recipient=recipient,
        purpose=purpose,
    )

    key = _make_otp_key(purpose, recipient)
    data = json.loads(redis_conn.get(key))
    code = data["code"]

    # Verify correctly
    ok, msg, remaining = verify_otp(redis_conn, recipient, purpose, code)
    assert ok is True
    assert "successfully" in msg

    # Redis key must be purged
    assert redis_conn.get(key) is None

    # Cannot verify again (already used)
    recheck_ok, recheck_msg, _ = verify_otp(redis_conn, recipient, purpose, code)
    assert recheck_ok is False
    assert "expired or was not requested" in recheck_msg


def test_otp_attempt_lockout_after_five_failures(db_session: Session, redis_conn):
    """Test that after 5 failed attempts, OTP is permanently invalidated in Redis."""
    recipient = f"lockout_{int(time.time())}@example.edu"
    purpose = "password_reset"

    store_and_send_otp(
        db=db_session,
        redis_client=redis_conn,
        recipient=recipient,
        purpose=purpose,
    )

    key = _make_otp_key(purpose, recipient)

    # Attempts 1 to 4 should decrement remaining
    for attempt in range(1, 5):
        ok, msg, remaining = verify_otp(redis_conn, recipient, purpose, "999999")
        assert ok is False
        expected_remaining = 5 - attempt
        assert remaining == expected_remaining
        assert f"{expected_remaining} attempt(s) remaining" in msg

    # 5th attempt must trigger lockout and invalidate OTP
    ok, msg, remaining = verify_otp(redis_conn, recipient, purpose, "999999")
    assert ok is False
    assert remaining == 0
    assert "Maximum verification attempts exceeded" in msg
    assert "invalidated" in msg

    # Key must be deleted from Redis
    assert redis_conn.get(key) is None


def test_otp_expired_or_missing(redis_conn):
    """Test that nonexistent or expired OTP returns clear failure message."""
    ok, msg, remaining = verify_otp(redis_conn, "ghost@example.edu", "login", "123456")
    assert ok is False
    assert remaining == 0
    assert "expired or was not requested" in msg


def test_otp_api_endpoints_send_and_verify(client: TestClient, db_session: Session, redis_conn):
    """Test /api/v1/auth/otp/send and /api/v1/auth/otp/verify HTTP endpoints."""
    recipient = f"api_otp_{int(time.time())}@example.edu"
    purpose = "consent"

    # Reset rate limit before call
    reset_rate_limit(redis_conn, "otp")

    # 1. Send OTP
    send_resp = client.post(
        "/api/v1/auth/otp/send",
        json={
            "recipient": recipient,
            "channel": "email",
            "purpose": purpose,
            "context": "Student record verification consent",
        },
    )
    assert send_resp.status_code == 200
    send_data = send_resp.json()
    assert send_data["status"] == "sent"
    assert send_data["recipient"] == recipient
    assert send_data["expires_in"] == 300

    # Read generated code from Redis
    key = _make_otp_key(purpose, recipient)
    stored = json.loads(redis_conn.get(key))
    code = stored["code"]

    # 2. Verify with invalid code
    bad_verify = client.post(
        "/api/v1/auth/otp/verify",
        json={"recipient": recipient, "purpose": purpose, "code": "000000"},
    )
    assert bad_verify.status_code == 400
    assert "attempt(s) remaining" in bad_verify.json()["detail"]

    # 3. Verify with valid code
    good_verify = client.post(
        "/api/v1/auth/otp/verify",
        json={"recipient": recipient, "purpose": purpose, "code": code},
    )
    assert good_verify.status_code == 200
    assert good_verify.json()["status"] == "verified"


# =============================================================================
# 2. TOTP MFA Tests for Admin Roles
# =============================================================================


def test_mfa_role_requirement_rules():
    """Verify admin roles require MFA while standard staff roles do not."""
    assert role_requires_mfa("college_admin") is True
    assert role_requires_mfa("aicte_admin") is True
    assert role_requires_mfa("aicte_officer") is True

    assert role_requires_mfa("college_staff") is False
    assert role_requires_mfa("college_viewer") is False
    assert role_requires_mfa("verifier") is False


def test_totp_generation_and_validation():
    """Test pyotp secret generation, URI construction, and TOTP code verification."""
    secret = generate_totp_secret()
    assert len(secret) == 32

    uri = get_totp_uri(secret, "admin@example.edu")
    assert uri.startswith("otpauth://totp/AICTE%20EduTrace:admin%40example.edu")
    assert f"secret={secret}" in uri

    # Valid current TOTP code
    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    assert verify_totp(secret, current_code) is True

    # Bad code
    assert verify_totp(secret, "000000") is False
    assert verify_totp("", current_code) is False


def test_mfa_setup_and_enable_flow(client: TestClient, db_session: Session):
    """Test user sets up TOTP and enables MFA via /auth/mfa/setup and /auth/mfa/enable."""
    _, user, _ = _create_institution_and_user(db_session, role="college_admin")
    token = create_access_token(user.id, user.email, user.role, user.institution_id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Setup endpoint: generates secret and URI
    setup_resp = client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup_resp.status_code == 200
    setup_data = setup_resp.json()
    secret = setup_data["secret"]
    assert "otpauth://" in setup_data["provisioning_uri"]

    # 2. Enable endpoint: fail with wrong code
    fail_enable = client.post(
        "/api/v1/auth/mfa/enable",
        headers=headers,
        json={"code": "123456", "secret": secret},
    )
    assert fail_enable.status_code == 400
    assert "Invalid verification code" in fail_enable.json()["detail"]

    # 3. Enable endpoint: succeed with valid code
    valid_code = pyotp.TOTP(secret).now()
    ok_enable = client.post(
        "/api/v1/auth/mfa/enable",
        headers=headers,
        json={"code": valid_code, "secret": secret},
    )
    assert ok_enable.status_code == 200
    assert ok_enable.json()["status"] == "mfa_enabled"

    # User in database should now have mfa_secret
    refreshed_user = db_session.scalar(select(User).where(User.id == user.id))
    assert refreshed_user.mfa_secret == secret


def test_admin_login_with_mfa_challenge_two_step(
    client: TestClient,
    db_session: Session,
    redis_conn,
):
    """Test two-step login for admin with MFA: challenge -> /auth/mfa/verify succeeds."""
    reset_rate_limit(redis_conn, "login")
    secret = generate_totp_secret()
    _, user, password = _create_institution_and_user(
        db_session,
        role="aicte_admin",
        mfa_secret=secret,
    )

    # Step 1: Login without mfa_code -> returns mfa_required=True and mfa_token
    step1_resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
    )
    assert step1_resp.status_code == 200
    step1_data = step1_resp.json()
    assert step1_data["mfa_required"] is True
    assert step1_data["mfa_token"] is not None
    assert step1_data["access_token"] == ""
    assert step1_data["refresh_token"] == ""

    mfa_token = step1_data["mfa_token"]

    # Step 2a: Submit bad TOTP code to /auth/mfa/verify -> 401 Unauthorized
    bad_mfa_resp = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": "000000"},
    )
    assert bad_mfa_resp.status_code == 401
    assert "Invalid MFA code" in bad_mfa_resp.json()["detail"]

    # Step 2b: Submit valid TOTP code to /auth/mfa/verify -> 200 OK with full token pair
    valid_totp = pyotp.TOTP(secret).now()
    good_mfa_resp = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": valid_totp},
    )
    assert good_mfa_resp.status_code == 200
    good_mfa_data = good_mfa_resp.json()
    assert good_mfa_data["mfa_required"] is False
    assert len(good_mfa_data["access_token"]) > 20
    assert len(good_mfa_data["refresh_token"]) > 20
    assert good_mfa_data["user"]["email"] == user.email


def test_admin_login_with_mfa_code_direct(client: TestClient, db_session: Session, redis_conn):
    """Test one-step login providing mfa_code directly in POST /api/v1/auth/login."""
    reset_rate_limit(redis_conn, "login")
    secret = generate_totp_secret()
    _, user, password = _create_institution_and_user(
        db_session,
        role="college_admin",
        mfa_secret=secret,
    )

    # 1. Invalid mfa_code -> 401
    bad_resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password, "mfa_code": "000000"},
    )
    assert bad_resp.status_code == 401
    assert "Invalid MFA code" in bad_resp.json()["detail"]

    # 2. Valid mfa_code -> 200 with tokens
    valid_code = pyotp.TOTP(secret).now()
    good_resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password, "mfa_code": valid_code},
    )
    assert good_resp.status_code == 200
    data = good_resp.json()
    assert data["mfa_required"] is False
    assert len(data["access_token"]) > 20
    assert len(data["refresh_token"]) > 20


# =============================================================================
# 3. Rate Limiting Tests (Login, OTP, and Verify endpoints returning 429)
# =============================================================================


def test_rate_limiter_login_endpoint(client: TestClient, db_session: Session, redis_conn):
    """Test rate limiting on login endpoint: exceeding limit returns 429 with Retry-After header."""
    reset_rate_limit(redis_conn, "login")
    _, user, password = _create_institution_and_user(db_session, role="college_staff")

    # Send requests up to configured limit
    limit = settings.RATE_LIMIT_LOGIN_PER_MINUTE
    for _ in range(limit):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": password},
        )
        assert resp.status_code == 200

    # Next request must exceed rate limit
    exceeded_resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
    )
    assert exceeded_resp.status_code == 429
    assert "Rate limit exceeded for login" in exceeded_resp.json()["detail"]
    assert "Retry-After" in exceeded_resp.headers
    retry_after = int(exceeded_resp.headers["Retry-After"])
    assert 1 <= retry_after <= 60

    # Reset allows requests again
    reset_rate_limit(redis_conn, "login")
    reset_resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
    )
    assert reset_resp.status_code == 200


def test_rate_limiter_otp_endpoint(client: TestClient, redis_conn):
    """Test rate limiting on OTP endpoints returns 429 and Retry-After."""
    reset_rate_limit(redis_conn, "otp")
    limit = settings.RATE_LIMIT_OTP_PER_MINUTE

    recipient = f"ratelimit_{int(time.time())}@example.edu"
    payload = {"recipient": recipient, "purpose": "login", "channel": "email"}

    for _ in range(limit):
        resp = client.post("/api/v1/auth/otp/send", json=payload)
        assert resp.status_code == 200

    # Exceed limit
    exceeded_resp = client.post("/api/v1/auth/otp/send", json=payload)
    assert exceeded_resp.status_code == 429
    assert "Rate limit exceeded for otp" in exceeded_resp.json()["detail"]
    assert "Retry-After" in exceeded_resp.headers

    # Reset
    reset_rate_limit(redis_conn, "otp")


def test_rate_limiter_verify_endpoint(client: TestClient, redis_conn):
    """Test rate limiting on verification endpoint returns 429 and Retry-After."""
    reset_rate_limit(redis_conn, "verify")
    limit = settings.RATE_LIMIT_VERIFY_PER_MINUTE

    for i in range(limit):
        resp = client.get(f"/api/v1/verification/verify?vid=TEST-VERIFY-{i}")
        assert resp.status_code == 200

    # Exceed limit
    exceeded_resp = client.get("/api/v1/verification/verify?vid=TEST-VERIFY-EXCEED")
    assert exceeded_resp.status_code == 429
    assert "Rate limit exceeded for verify" in exceeded_resp.json()["detail"]
    assert "Retry-After" in exceeded_resp.headers

    # Reset
    reset_rate_limit(redis_conn, "verify")
