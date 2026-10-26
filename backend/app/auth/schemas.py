"""Pydantic schemas for authentication and RBAC."""

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
    def all_roles(cls) -> set[str]:
        return {r.value for r in cls}


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, description="User's login email address")
    password: str = Field(..., min_length=1, description="Account password")



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
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
