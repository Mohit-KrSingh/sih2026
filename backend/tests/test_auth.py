"""Unit and integration tests for authentication: Argon2, JWT, and auth endpoints."""

import time
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.models import Institution, User

settings = get_settings()


def _create_test_institution(db: Session, aicte_id: str = "TEST-INST-01") -> Institution:
    inst = Institution(
        aicte_id=aicte_id,
        name=f"Test Institution {aicte_id}",
        state="Maharashtra",
        district="Pune",
        address="123 Test Street",
        official_email=f"official_{aicte_id.lower()}@example.edu",
        official_phone="+919876543210",
        head_name="Dr. Test Head",
        affiliating_university="Test University",
        approval_status="active",
        account_status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def test_argon2_hashing_and_verification():
    """Test Argon2 password hashing and verification behavior."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    # Hash should be distinct from plaintext and use argon2id prefix
    assert hashed != password
    assert "$argon2id$" in hashed

    # Valid password verification
    assert verify_password(password, hashed) is True

    # Invalid password verification
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False

    # Corrupted / invalid hash string
    assert verify_password(password, "invalid_hash_string") is False
    assert verify_password(password, "") is False


def test_jwt_access_and_refresh_token_generation_and_decoding():
    """Test JWT token creation, claims, and signature validation."""
    access_token = create_access_token(
        user_id=42,
        email="test.user@example.com",
        role="college_admin",
        institution_id=7,
        expires_delta=timedelta(minutes=15),
    )
    decoded_access = decode_token(access_token)
    assert decoded_access["sub"] == "42"
    assert decoded_access["email"] == "test.user@example.com"
    assert decoded_access["role"] == "college_admin"
    assert decoded_access["institution_id"] == 7
    assert decoded_access["type"] == "access"
    assert "exp" in decoded_access
    assert "iat" in decoded_access
    assert "jti" in decoded_access

    refresh_token = create_refresh_token(
        user_id=42,
        email="test.user@example.com",
        role="college_admin",
        institution_id=7,
        expires_delta=timedelta(days=7),
    )
    decoded_refresh = decode_token(refresh_token)
    assert decoded_refresh["sub"] == "42"
    assert decoded_refresh["type"] == "refresh"


def test_jwt_token_expiration_and_tampering():
    """Test that expired or tampered tokens are rejected."""
    # Token that expired 5 seconds ago
    expired_token = create_access_token(
        user_id=1,
        email="expired@example.com",
        role="aicte_admin",
        expires_delta=timedelta(seconds=-5),
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired_token)

    # Token signed with wrong secret
    tampered_token = jwt.encode(
        {"sub": "1", "email": "hacker@example.com", "role": "aicte_admin", "type": "access"},
        "wrong-secret-key-that-does-not-match",
        algorithm="HS256",
    )
    with pytest.raises(jwt.PyJWTError):
        decode_token(tampered_token)


def test_auth_login_endpoint_success_and_failure(client: TestClient, db_session: Session):
    """Test POST /api/v1/auth/login with valid and invalid credentials."""
    inst = _create_test_institution(db_session, aicte_id=f"TEST-LOGIN-{int(time.time())}")
    email = f"auth_test_{int(time.time())}@example.com"
    raw_password = "SecretPassword123"
    hashed = hash_password(raw_password)

    user = User(
        email=email,
        password_hash=hashed,
        role="college_admin",
        institution_id=inst.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 1. Successful login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": raw_password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email
    assert data["user"]["role"] == "college_admin"
    assert data["user"]["institution_id"] == inst.id

    # Verify last_login was updated
    updated_user = db_session.scalar(select(User).where(User.id == user.id))
    assert updated_user.last_login is not None

    # 2. Failed login: wrong password
    bad_pass_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword"},
    )
    assert bad_pass_response.status_code == 401
    assert "Invalid email or password" in bad_pass_response.json()["detail"]

    # 3. Failed login: nonexistent user
    unknown_response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": raw_password},
    )
    assert unknown_response.status_code == 401

    # 4. Deactivated user login fails with 403
    user.is_active = False
    db_session.commit()

    deactivated_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": raw_password},
    )
    assert deactivated_response.status_code == 403
    assert "deactivated" in deactivated_response.json()["detail"].lower()


def test_auth_refresh_token_endpoint(client: TestClient, db_session: Session):
    """Test POST /api/v1/auth/refresh for issuing new tokens."""
    email = f"refresh_test_{int(time.time())}@example.com"
    user = User(
        email=email,
        password_hash=hash_password("DemoPass123"),
        role="aicte_officer",
        institution_id=None,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    refresh_token = create_refresh_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    # 1. Valid refresh
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert "access_token" in data
    assert data["user"]["email"] == email

    # 2. Using an access token instead of a refresh token should fail
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )
    wrong_type_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert wrong_type_response.status_code == 401
    assert "expected refresh token" in wrong_type_response.json()["detail"].lower()

    # 3. Malformed token fails
    malformed_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-valid-jwt-token"},
    )
    assert malformed_response.status_code == 401


def test_auth_me_endpoint(client: TestClient, db_session: Session):
    """Test GET /api/v1/auth/me profile endpoint."""
    email = f"me_test_{int(time.time())}@example.com"
    user = User(
        email=email,
        password_hash=hash_password("DemoPass123"),
        role="verifier",
        institution_id=None,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    # 1. Authenticated request
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    profile = response.json()
    assert profile["id"] == user.id
    assert profile["email"] == email
    assert profile["role"] == "verifier"

    # 2. Unauthenticated request
    no_auth_response = client.get("/api/v1/auth/me")
    assert no_auth_response.status_code == 401

    # 3. Invalid token
    bad_token_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.payload"},
    )
    assert bad_token_response.status_code == 401
