"""DPDP-aligned privacy policy and data minimisation specification endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["privacy"])


class FieldMetadata(BaseModel):
    field: str
    group: str
    description: str
    storage: str


class ProhibitedField(BaseModel):
    field: str
    reason: str


class DataMinimisationSpec(BaseModel):
    collected_fields: list[FieldMetadata]
    prohibited_fields: list[ProhibitedField]


class DataFiduciaryInfo(BaseModel):
    name: str
    ministry: str
    statutory_mandate: str


class CryptographicSafeguards(BaseModel):
    dob_encryption: str
    apaar_log_redaction: str
    audit_trail: str
    verifiable_credentials: str


class ConsentFrameworkSpec(BaseModel):
    statutory_ttl_hours: int = 24
    single_use_enforced: bool = True
    student_revocation_right: bool = True
    minimal_disclosure_fields: list[str]
    restricted_from_verifiers: list[str]


class DataRetentionPolicy(BaseModel):
    student_enrolment_records: str
    consent_requests: str
    audit_log: str


class GrievanceRedressalInfo(BaseModel):
    officer: str
    designation: str
    email: str
    address: str
    resolution_sla: str


class PrivacyPolicyResponse(BaseModel):
    status: str = "compliant"
    framework: str = "Digital Personal Data Protection Act (DPDP), 2023"
    effective_date: str = "2026-01-01"
    data_fiduciary: DataFiduciaryInfo
    purpose_limitation: list[str]
    data_minimisation: DataMinimisationSpec
    cryptographic_safeguards: CryptographicSafeguards
    consent_framework: ConsentFrameworkSpec
    data_principal_rights: list[str]
    data_retention: DataRetentionPolicy
    grievance_redressal: GrievanceRedressalInfo


PRIVACY_POLICY_DATA = PrivacyPolicyResponse(
    status="compliant",
    framework="Digital Personal Data Protection Act (DPDP), 2023",
    effective_date="2026-01-01",
    data_fiduciary=DataFiduciaryInfo(
        name="All India Council for Technical Education (AICTE)",
        ministry="Ministry of Education, Government of India",
        statutory_mandate="AICTE Act 1987 & National Technical Education Regulations",
    ),
    purpose_limitation=[
        "Academic enrolment record management keyed by APAAR ID",
        "Reconciliation of institutional intake quotas and supernumerary caps",
        "Automated detection and prevention of concurrent cross-college duplicate enrolments",
        "Live regulatory compliance monitoring and anomaly alerts for AICTE officers",
        "Consent-gated verifiable academic credential issuance for authorised verifiers",
    ],
    data_minimisation=DataMinimisationSpec(
        collected_fields=[
            FieldMetadata(
                field="apaar_id",
                group="Identity",
                description="12-digit national academic identifier",
                storage="Plaintext indexed",
            ),
            FieldMetadata(
                field="name",
                group="Identity",
                description="Student full name",
                storage="Plaintext",
            ),
            FieldMetadata(
                field="dob",
                group="Identity",
                description="Date of birth",
                storage="Encrypted at rest (Fernet AES-128-CBC + HMAC-SHA256)",
            ),
            FieldMetadata(
                field="gender",
                group="Identity",
                description="Gender (Male, Female, Other)",
                storage="Plaintext",
            ),
            FieldMetadata(
                field="course",
                group="Admission",
                description="Approved academic course/program",
                storage="Plaintext foreign key",
            ),
            FieldMetadata(
                field="branch",
                group="Admission",
                description="Approved technical engineering/technology branch",
                storage="Plaintext",
            ),
            FieldMetadata(
                field="admission_year",
                group="Admission",
                description="Academic year of admission (e.g. 2026-27)",
                storage="Plaintext indexed",
            ),
            FieldMetadata(
                field="enrolment_no",
                group="Admission",
                description="College's own internal student roll/enrolment ID",
                storage="Plaintext unique within course",
            ),
            FieldMetadata(
                field="admission_date",
                group="Admission",
                description="Calendar date of official admission",
                storage="ISO date",
            ),
            FieldMetadata(
                field="admission_mode",
                group="Admission",
                description="Admission channel (JEE Main, State, Management, etc.)",
                storage="Enum string",
            ),
            FieldMetadata(
                field="seat_type",
                group="Admission",
                description="Seat allocation type (Regular or Supernumerary)",
                storage="Enum string",
            ),
            FieldMetadata(
                field="reservation_category",
                group="Category",
                description="Statutory reservation category (General, OBC, SC, ST, EWS)",
                storage="Enum string",
            ),
            FieldMetadata(
                field="nri",
                group="Category",
                description="Non-Resident Indian status (Yes or No)",
                storage="Flag string",
            ),
            FieldMetadata(
                field="oci",
                group="Category",
                description="Overseas Citizen of India status (Yes or No)",
                storage="Flag string",
            ),
            FieldMetadata(
                field="foreign_national",
                group="Category",
                description="Foreign national status (Yes or No)",
                storage="Flag string",
            ),
            FieldMetadata(
                field="country",
                group="Category",
                description="Country of citizenship (only for foreign nationals)",
                storage="String or null",
            ),
        ],
        prohibited_fields=[
            ProhibitedField(
                field="Aadhaar / National Identity Numbers",
                reason=(
                    "Hard Rule 2: APAAR ID is the sole statutory student identifier; "
                    "Aadhaar is strictly prohibited."
                ),
            ),
            ProhibitedField(
                field="Parents / Guardians Personal Information",
                reason="Non-essential for higher educational enrollment verification.",
            ),
            ProhibitedField(
                field="Residential Address & Geolocation Data",
                reason="Excluded under DPDP data minimisation; not required for regulatory audit.",
            ),
            ProhibitedField(
                field="Photographs & Biometric Signatures",
                reason="No facial recognition or biometric data is collected or processed.",
            ),
            ProhibitedField(
                field="Family Income & Financial Statements",
                reason="Financial background is outside the scope of central intake tracking.",
            ),
            ProhibitedField(
                field="Examination Marks & Academic Transcripts",
                reason="Maintained by individual institutional ERPs; only enrollment is tracked.",
            ),
        ],
    ),
    cryptographic_safeguards=CryptographicSafeguards(
        dob_encryption="Fernet 128-bit AES-CBC mode with PKCS7 padding and HMAC-SHA256",
        apaar_log_redaction="Automated regex masking in runtime logs (redacted to ********<last4>)",
        audit_trail="Tamper-evident append-only hash chaining: SHA256(prev_hash + canonical_row)",
        verifiable_credentials="High-assurance Ed25519 digital signatures over canonical JSON",
    ),
    consent_framework=ConsentFrameworkSpec(
        statutory_ttl_hours=24,
        single_use_enforced=True,
        student_revocation_right=True,
        minimal_disclosure_fields=[
            "institution",
            "course",
            "years",
            "status",
            "verification_id",
            "verified_by",
        ],
        restricted_from_verifiers=[
            "dob",
            "reservation_category",
            "nri_oci_status",
            "contact_information",
        ],
    ),
    data_principal_rights=[
        "Right to Access: Students can view all institutions holding records under APAAR ID.",
        "Right to Consent Control: Students may review, approve, or deny verification requests.",
        "Right to Consent History: Complete audit trail of historical verification requests.",
        "Right to Grievance Redressal: Direct grievance mechanism with the AICTE DPO.",
    ],
    data_retention=DataRetentionPolicy(
        student_enrolment_records=(
            "Retained for the duration of the student's academic degree tenure "
            "plus statutory regulatory audit period."
        ),
        consent_requests=(
            "24 hours active validity; decision audit trail retained in append-only log."
        ),
        audit_log=(
            "Permanent tamper-evident cryptographic log for regulatory non-repudiation."
        ),
    ),
    grievance_redressal=GrievanceRedressalInfo(
        officer="Data Protection Officer (DPO), AICTE Central Repository",
        designation="Director (Legal Compliance & Data Protection)",
        email="dpo@aicte-india.org",
        address="AICTE Headquarters, Nelson Mandela Marg, Vasant Kunj, New Delhi - 110070",
        resolution_sla="30 days statutory response window",
    ),
)


@router.get(
    "/privacy",
    response_model=PrivacyPolicyResponse,
    summary="Get DPDP Privacy Policy & Data Minimisation Statement",
    description=(
        "Public endpoint returning the comprehensive Digital Personal Data Protection (DPDP) "
        "compliance statement, data minimisation schema, consent framework, and DPO contacts."
    ),
)
def get_privacy_policy() -> PrivacyPolicyResponse:
    """Return the official DPDP privacy policy and data minimisation specification."""
    return PRIVACY_POLICY_DATA
