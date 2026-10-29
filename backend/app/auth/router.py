"""Authentication API router: login, token refresh, user profile, TOTP MFA, and OTP."""

from datetime import UTC, datetime
from typing import Annotated

import jwt
import redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.auth.dependencies import get_current_user, verify_institution_access
from app.auth.otp import store_and_send_otp, verify_otp
from app.auth.rate_limiter import RateLimiter, _extract_client_ip
from app.auth.schemas import (
    LoginRequest,
    MfaEnableRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    PasswordResetVerifyRequest,
    PasswordResetVerifyResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_password_reset_token,
    decode_token,
    hash_password,
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
from app.institutions.service import mask_email
from app.models import Institution, User

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
    request: Request,
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

    # Spec 11: Non-approved colleges cannot log in
    if user.institution_id is not None:
        inst = db.get(Institution, user.institution_id)
        if inst is None or inst.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Institution account is not activated or approved by AICTE",
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
    audit.record(
        db=db,
        action="auth.login",
        actor_id=str(user.id),
        actor_role=user.role,
        entity="user",
        entity_id=str(user.id),
        after_json={"email": user.email, "role": user.role},
        ip=_extract_client_ip(request),
    )
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
    request: Request,
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

    # Spec 11: Non-approved colleges cannot log in
    if user.institution_id is not None:
        inst = db.get(Institution, user.institution_id)
        if inst is None or inst.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Institution account is not activated or approved by AICTE",
            )

    if not user.mfa_secret or not verify_totp(user.mfa_secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login = datetime.now(UTC)
    audit.record(
        db=db,
        action="auth.login_mfa",
        actor_id=str(user.id),
        actor_role=user.role,
        entity="user",
        entity_id=str(user.id),
        after_json={"email": user.email, "role": user.role, "mfa_method": "totp"},
        ip=_extract_client_ip(request),
    )
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
        issuer="AICTE EduTrace",
        account_email=current_user.email,
    )


@router.post("/mfa/enable")
def enable_mfa(
    payload: MfaEnableRequest,
    request: Request,
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
    audit.record(
        db=db,
        action="auth.mfa_enable",
        actor_id=str(current_user.id),
        actor_role=current_user.role,
        entity="user",
        entity_id=str(current_user.id),
        after_json={"mfa_enabled": True},
        ip=_extract_client_ip(request),
    )
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

    # Spec 11: Non-approved colleges cannot log in
    if user.institution_id is not None:
        inst = db.get(Institution, user.institution_id)
        if inst is None or inst.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Institution account is not activated or approved by AICTE",
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


# Password Reset Endpoints (Spec 11, TASKS.md T09)

password_reset_req_limiter = RateLimiter(
    times=settings.RATE_LIMIT_OTP_PER_MINUTE,
    seconds=60,
    label="pwd_reset_req",
)
password_reset_verify_limiter = RateLimiter(
    times=10,
    seconds=60,
    label="pwd_reset_verify",
)
password_reset_confirm_limiter = RateLimiter(
    times=10,
    seconds=60,
    label="pwd_reset_confirm",
)


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
    dependencies=[Depends(password_reset_req_limiter)],
    summary="Request password reset OTP dispatched strictly to on-file contact",
)
def request_password_reset(
    payload: PasswordResetRequest,
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> PasswordResetRequestResponse:
    """Initiate password reset flow.

    Spec 11:
    - Password reset ONLY via OTP to the official contacts on file.
    - OTP is NEVER sent to a typed-in address.
    - For college users, OTP is dispatched strictly to the institution's official_email.
    - For AICTE users without an institution, OTP is dispatched to user.email on file.
    """
    clean_email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == clean_email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{clean_email}' not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    if user.institution_id is not None:
        inst = db.get(Institution, user.institution_id)
        if inst is None or inst.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Institution account is not activated or approved by AICTE",
            )
        official_recipient = inst.official_email
        context = f"Password reset OTP for user {clean_email} under institution {inst.aicte_id}"
    else:
        official_recipient = user.email
        context = f"Password reset OTP for administrative user {clean_email}"

    store_and_send_otp(
        db=db,
        redis_client=redis_client,
        recipient=official_recipient,
        channel="email",
        purpose="password_reset",
        context=context,
    )

    return PasswordResetRequestResponse(
        status="success",
        message="One-time verification code has been dispatched to official on-file contact.",
        masked_recipient=mask_email(official_recipient),
        channel="email",
    )


@router.post(
    "/password-reset/verify",
    response_model=PasswordResetVerifyResponse,
    dependencies=[Depends(password_reset_verify_limiter)],
    summary="Verify password reset OTP and obtain password reset token",
)
def verify_password_reset(
    payload: PasswordResetVerifyRequest,
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> PasswordResetVerifyResponse:
    """Verify OTP sent to on-file contact and issue short-lived password reset token."""
    clean_email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == clean_email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{clean_email}' not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    if user.institution_id is not None:
        inst = db.get(Institution, user.institution_id)
        if inst is None or inst.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Institution account is not activated",
            )
        official_recipient = inst.official_email
    else:
        official_recipient = user.email

    is_valid, msg, remaining = verify_otp(
        redis_client=redis_client,
        recipient=official_recipient,
        purpose="password_reset",
        code=payload.otp_code.strip(),
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    reset_token = create_password_reset_token(user_id=user.id, email=user.email)
    return PasswordResetVerifyResponse(
        status="success",
        message="OTP verified successfully. You may now reset your password.",
        reset_token=reset_token,
        expires_in=900,
    )


@router.post(
    "/password-reset/confirm",
    response_model=PasswordResetConfirmResponse,
    dependencies=[Depends(password_reset_confirm_limiter)],
    summary="Confirm new password using verified reset token",
)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> PasswordResetConfirmResponse:
    """Update user password using verified reset token and audit log the change."""
    try:
        token_data = decode_password_reset_token(payload.reset_token)
    except (jwt.PyJWTError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired password reset token. Please request a new OTP.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user_id = int(token_data["sub"])
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)

    client_ip = request.client.host if request.client else None
    audit.record(
        db=db,
        action="auth.password_reset",
        actor_id=user.id,
        actor_role=user.role,
        entity="users",
        entity_id=user.id,
        before_json={"email": user.email},
        after_json={"email": user.email, "status": "password_reset_success"},
        ip=client_ip,
    )

    return PasswordResetConfirmResponse(
        status="success",
        message=(
            "Password has been successfully updated. You may now log in with your new password."
        ),
    )
