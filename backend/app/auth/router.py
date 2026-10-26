"""Authentication API router: login, token refresh, user profile, TOTP MFA, and OTP."""

from datetime import UTC, datetime
from typing import Annotated

import jwt
import redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, verify_institution_access
from app.auth.otp import store_and_send_otp, verify_otp
from app.auth.rate_limiter import RateLimiter
from app.auth.schemas import (
    LoginRequest,
    MfaEnableRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.auth.totp import (
    create_mfa_pending_token,
    decode_mfa_pending_token,
    generate_totp_secret,
    get_totp_uri,
    verify_totp,
)
from app.config import get_settings
from app.db import get_db, get_redis
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

login_rate_limiter = RateLimiter(
    times=settings.RATE_LIMIT_LOGIN_PER_MINUTE,
    seconds=60,
    label="login",
)
otp_rate_limiter = RateLimiter(
    times=settings.RATE_LIMIT_OTP_PER_MINUTE,
    seconds=60,
    label="otp",
)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(login_rate_limiter)],
)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Authenticate with email and password.

    If the user has TOTP MFA enabled, requires an MFA verification code
    either in this request or via a subsequent /auth/mfa/verify step.
    """
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Check Multi-Factor Authentication requirement
    if user.mfa_secret:
        if payload.mfa_code:
            # Code provided upfront in login request
            if not verify_totp(user.mfa_secret, payload.mfa_code):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA code",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        else:
            # 2-step MFA flow: issue temporary intermediate token
            mfa_pending_token = create_mfa_pending_token(
                user_id=user.id,
                email=user.email,
                role=user.role,
                institution_id=user.institution_id,
            )
            return TokenResponse(
                access_token="",
                refresh_token="",
                token_type="bearer",
                expires_in=300,
                user=UserResponse.model_validate(user),
                mfa_required=True,
                mfa_token=mfa_pending_token,
            )

    user.last_login = datetime.now(UTC)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    refresh_token = create_refresh_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
        mfa_required=False,
    )


@router.post(
    "/mfa/verify",
    response_model=TokenResponse,
    dependencies=[Depends(login_rate_limiter)],
)
def verify_mfa_login(
    payload: MfaVerifyRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Complete 2-step login by validating a TOTP code against an MFA pending token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired MFA session token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        decoded = decode_mfa_pending_token(payload.mfa_token)
    except (jwt.PyJWTError, Exception):
        raise credentials_exception from None

    user_id_raw = decoded.get("sub")
    if not user_id_raw:
        raise credentials_exception

    try:
        user_id = int(user_id_raw)
    except ValueError:
        raise credentials_exception from None

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise credentials_exception

    if not user.mfa_secret or not verify_totp(user.mfa_secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login = datetime.now(UTC)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    refresh_token = create_refresh_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
        mfa_required=False,
    )


@router.post("/mfa/setup", response_model=MfaSetupResponse)
def setup_mfa(
    current_user: Annotated[User, Depends(get_current_user)],
) -> MfaSetupResponse:
    """Generate a new TOTP secret and provisioning URI for the authenticated user."""
    secret = generate_totp_secret()
    uri = get_totp_uri(secret=secret, account_email=current_user.email)

    return MfaSetupResponse(
        secret=secret,
        provisioning_uri=uri,
        issuer="AICTE APAAR",
        account_email=current_user.email,
    )


@router.post("/mfa/enable")
def enable_mfa(
    payload: MfaEnableRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Verify and persist TOTP secret to activate MFA for the user."""
    if not verify_totp(payload.secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code. Ensure your authenticator app time is synchronized.",
        )

    current_user.mfa_secret = payload.secret
    db.commit()

    return {
        "status": "mfa_enabled",
        "message": "Multi-Factor Authentication has been successfully enabled.",
    }


@router.post(
    "/otp/send",
    response_model=OtpSendResponse,
    dependencies=[Depends(otp_rate_limiter)],
)
def send_otp_endpoint(
    payload: OtpSendRequest,
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> OtpSendResponse:
    """Generate and dispatch a 6-digit verification OTP (valid for 5 minutes)."""
    result = store_and_send_otp(
        db=db,
        redis_client=redis_client,
        recipient=payload.recipient,
        channel=payload.channel,
        purpose=payload.purpose,
        context=payload.context,
    )
    return OtpSendResponse(**result)


@router.post(
    "/otp/verify",
    response_model=OtpVerifyResponse,
    dependencies=[Depends(otp_rate_limiter)],
)
def verify_otp_endpoint(
    payload: OtpVerifyRequest,
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> OtpVerifyResponse:
    """Verify an OTP code with 5 attempts max before lockout."""
    ok, message, _remaining = verify_otp(
        redis_client=redis_client,
        recipient=payload.recipient,
        purpose=payload.purpose,
        code=payload.code,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    return OtpVerifyResponse(status="verified", message=message)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    payload: RefreshTokenRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Issue a new access token using a valid refresh token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        decoded = decode_token(payload.refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.PyJWTError:
        raise credentials_exception from None

    if decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: expected refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_raw = decoded.get("sub")
    if not user_id_raw:
        raise credentials_exception

    try:
        user_id = int(user_id_raw)
    except ValueError:
        raise credentials_exception from None

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    new_access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    new_refresh_token = create_refresh_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
        mfa_required=False,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Retrieve the authenticated user's profile and active role."""
    return UserResponse.model_validate(current_user)


@router.get("/institutions/{institution_id}/access-check")
def check_institution_permission(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str | int]:
    """Verify institution scoping.

    Colleges can only access their own institution.
    AICTE officers can supervise all institutions.
    """
    return {
        "status": "granted",
        "institution_id": institution_id,
        "user_id": current_user.id,
        "role": current_user.role,
    }
