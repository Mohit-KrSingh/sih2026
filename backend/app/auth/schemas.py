"""Pydantic schemas for authentication, RBAC, MFA and OTP."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Role(StrEnum):
    AICTE_ADMIN = "aicte_admin"
    AICTE_OFFICER = "aicte_officer"
    COLLEGE_ADMIN = "college_admin"
    COLLEGE_STAFF = "college_staff"
    COLLEGE_VIEWER = "college_viewer"
    VERIFIER = "verifier"

    @classmethod
    def aicte_roles(cls) -> set[str]:
        return {cls.AICTE_ADMIN.value, cls.AICTE_OFFICER.value}

    @classmethod
    def college_roles(cls) -> set[str]:
        return {
            cls.COLLEGE_ADMIN.value,
            cls.COLLEGE_STAFF.value,
            cls.COLLEGE_VIEWER.value,
        }

    @classmethod
    def admin_roles(cls) -> set[str]:
        return {
            cls.AICTE_ADMIN.value,
            cls.AICTE_OFFICER.value,
            cls.COLLEGE_ADMIN.value,
        }

    @classmethod
    def all_roles(cls) -> set[str]:
        return {r.value for r in cls}


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, description="User's login email address")
    password: str = Field(..., min_length=1, description="Account password")
    mfa_code: str | None = Field(
        None,
        min_length=6,
        max_length=8,
        description="Optional 6-digit TOTP code for MFA accounts",
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid JWT refresh token")


class UserSummary(BaseModel):
    id: int
    email: str
    role: str
    institution_id: int | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    institution_id: int | None = None
    is_active: bool
    last_login: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str = Field(default="", description="JWT access token")
    refresh_token: str = Field(default="", description="JWT refresh token")
    token_type: str = "bearer"
    expires_in: int = Field(default=1800, description="Token validity in seconds")
    user: UserResponse
    mfa_required: bool = Field(default=False, description="Whether TOTP MFA code is required")
    mfa_token: str | None = Field(
        default=None,
        description="Intermediate token for completing MFA challenge",
    )


class MfaVerifyRequest(BaseModel):
    mfa_token: str = Field(..., description="Intermediate JWT token from login step")
    code: str = Field(
        ...,
        min_length=6,
        max_length=8,
        description="6-digit TOTP authenticator code",
    )


class MfaSetupResponse(BaseModel):
    secret: str = Field(..., description="Base32 TOTP secret key")
    provisioning_uri: str = Field(..., description="otpauth:// URI for authenticator apps")
    issuer: str = "AICTE APAAR"
    account_email: str


class MfaEnableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8, description="6-digit TOTP code from app")
    secret: str = Field(..., description="Base32 secret returned by setup")


class OtpSendRequest(BaseModel):
    recipient: str = Field(..., min_length=3, description="Email address or phone number")
    channel: str = Field(default="email", description="Channel: email or sms")
    purpose: str = Field(
        default="general",
        description="Purpose: activation, login, reset, consent, declaration",
    )
    context: str = Field(default="", description="Optional human-readable context")


class OtpSendResponse(BaseModel):
    status: str
    recipient: str
    channel: str
    purpose: str
    expires_in: int
    message: str


class OtpVerifyRequest(BaseModel):
    recipient: str = Field(..., min_length=3, description="Email address or phone number")
    purpose: str = Field(..., description="Purpose matching the send request")
    code: str = Field(..., min_length=4, max_length=8, description="One-time verification code")


class OtpVerifyResponse(BaseModel):
    status: str
    message: str
