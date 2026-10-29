"""Pydantic schemas for verifier onboarding and student consent."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Verifier Onboarding Schemas


class VerifierRegisterRequest(BaseModel):
    """Payload for verifier organization self-registration."""

    org_name: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Legal name of verifying organisation (employer, regulator, or institution)",
        examples=["Tata Consultancy Services - Background Verifications"],
    )
    org_type: Literal["employer", "regulator", "institution"] = Field(
        ...,
        description="Organisation category per SPEC.md section 7",
        examples=["employer"],
    )
    contact: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Official contact email address for notifications and verifier user login",
        examples=["verifier@tcs-verifications.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Account password for verifier portal access",
        examples=["VerifierSecure123!"],
    )


class VerifierResponse(BaseModel):
    """Verifier organisation profile and onboarding status."""

    id: int
    org_name: str
    org_type: str
    contact: str
    status: Literal["pending", "approved", "revoked"]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerifierListResponse(BaseModel):
    """Paginated list of verifier organisations for AICTE admin review."""

    items: list[VerifierResponse]
    total: int


class VerifierStatusUpdateRequest(BaseModel):
    """Decision payload for AICTE admin to approve or revoke a verifier organisation."""

    status: Literal["approved", "revoked"] = Field(
        ...,
        description="Updated verifier status",
    )
    note: str | None = Field(
        None,
        max_length=500,
        description="Optional administrative note or statutory reason",
    )


# Consent Request Schemas


class ConsentRequestCreate(BaseModel):
    """Verifier payload to initiate a student consent request."""

    apaar_id: str = Field(
        ...,
        pattern=r"^\d{12}$",
        description="Target student 12-digit APAAR ID",
        examples=["111122223333"],
    )
    purpose: str = Field(
        default="Pre-employment or academic background verification",
        min_length=5,
        max_length=255,
        description="Explicit stated purpose aligned with DPDP consent requirements",
        examples=["Employment background check for Tata Consultancy Services"],
    )


class ConsentRequestResponse(BaseModel):
    """Full consent request details including scope, status, and expiry."""

    id: int
    verifier_id: int
    verifier_name: str
    verifier_type: str
    apaar_id: str
    status: str  # pending | approved | denied | expired | used
    purpose: str
    scope_fields: list[str]
    requested_at: datetime
    decided_at: datetime | None = None
    expires_at: datetime
    is_expired: bool = False
    is_used: bool = False

    model_config = ConfigDict(from_attributes=True)


class ConsentRequestListResponse(BaseModel):
    """List of consent requests."""

    items: list[ConsentRequestResponse]
    total: int


class ConsentDecisionRequest(BaseModel):
    """Student decision to approve or deny a pending consent request."""

    decision: Literal["approved", "denied"] = Field(
        ...,
        description="Student decision for consent request",
    )


# Student Portal Schemas


class StudentOtpRequest(BaseModel):
    """Student portal login initiation request."""

    apaar_id: str = Field(
        ...,
        pattern=r"^\d{12}$",
        description="12-digit national academic APAAR ID",
        examples=["111122223333"],
    )


class StudentOtpVerifyRequest(BaseModel):
    """Student portal OTP verification and session issuance."""

    apaar_id: str = Field(
        ...,
        pattern=r"^\d{12}$",
        description="12-digit national academic APAAR ID",
        examples=["111122223333"],
    )
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit numeric OTP delivered to student on-file contact",
        examples=["123456"],
    )


class StudentTokenResponse(BaseModel):
    """Student portal authenticated session response."""

    access_token: str
    token_type: str = "bearer"
    apaar_id: str
    student_name: str | None = None
    expires_in_hours: int = 24


class StudentAcademicRecordItem(BaseModel):
    """Academic record overview shown in student portal."""

    student_id: int | None = None
    enrolment_no: str | None = None
    institution_id: int
    institution_name: str
    institution_aicte_id: str
    course_id: int | None
    course_name: str
    academic_year: str
    status: str
    verification_id: str | None = None
    issued_at: datetime | None = None


class StudentRecordsListResponse(BaseModel):
    """List of academic institutional records holding the student's APAAR ID."""

    apaar_id: str
    records: list[StudentAcademicRecordItem]
    total: int


# Minimal Disclosure Consented Record Schema


class ConsentedStudentRecordResponse(BaseModel):
    """Minimal student academic verification record released to verifier upon consent.

    SPEC.md Section 14 & TASKS.md T33:
    - On approval the verifier sees only: institution, course, years, status,
      verification ID, and "verified by AICTE".
    - NEVER DOB, category, or contact data (strict DPDP data minimisation).
    - Single use: accessed once, then consumed.
    """

    institution: str
    course: str
    years: str
    status: str
    verification_id: str
    verified_by: str = "AICTE Central Repository"
    verified: bool = True
    purpose: str
    accessed_at: datetime
    consent_request_id: int
    verifier_name: str
    message: str = (
        "Academic record verified with authorized student consent under "
        "DPDP data minimisation policy."
    )
