"""External integration interfaces.

Every external service (APAAR registry, AICTE master list, OTP/SMS/email,
identity verification, file storage) sits behind an interface with a mock implementation.
Real implementations are stubs that raise NotImplementedError with a clear message.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ApaarRecord:
    """Standardized APAAR registry identity record."""

    apaar_id: str
    name: str
    dob: date
    gender: str


@runtime_checkable
class ApaarClient(Protocol):
    """Interface for APAAR ID identity verification registry."""

    def lookup(self, apaar_id: str) -> ApaarRecord | None:
        """Fetch a single record by 12-digit APAAR ID."""
        ...

    def lookup_batch(self, apaar_ids: list[str]) -> dict[str, ApaarRecord | None]:
        """Fetch multiple APAAR records in a single batch query."""
        ...


@dataclass(frozen=True)
class AicteCourseInfo:
    """Course approved by AICTE with approved intake parameters."""

    name: str
    level: str  # UG | PG | Diploma | PGDM
    branch: str
    duration_years: int
    supernumerary_allowed: bool = False
    approved_intake: int = 60
    supernumerary_seats_allowed: int = 0


@dataclass(frozen=True)
class AicteInstitutionInfo:
    """AICTE master registry institution information."""

    aicte_id: str
    name: str
    state: str
    district: str
    address: str
    official_email: str
    official_phone: str
    head_name: str
    affiliating_university: str
    approval_status: str = "active"  # active | suspended | withdrawn | expired
    approval_valid_to: date | None = None
    courses: list[AicteCourseInfo] = field(default_factory=list)


@runtime_checkable
class AicteMasterClient(Protocol):
    """Interface for AICTE Master Registry (institutions, courses, and intake)."""

    def get_institution(self, aicte_id: str) -> AicteInstitutionInfo | None:
        """Retrieve an approved institution by AICTE ID."""
        ...

    def list_institutions(self) -> list[AicteInstitutionInfo]:
        """List all approved institutions in the master registry."""
        ...

    def get_courses(self, aicte_id: str) -> list[AicteCourseInfo]:
        """List approved courses for an institution."""
        ...


@dataclass(frozen=True)
class OutboxMessage:
    """Transactional notification or OTP outbox item."""

    id: int | None
    channel: str  # otp | email | sms | notification
    recipient: str
    body: str


@runtime_checkable
class OtpSender(Protocol):
    """Interface for sending OTPs, SMS, and transactional notifications."""

    def send_otp(self, channel: str, recipient: str, code: str, context: str = "") -> bool:
        """Send a one-time verification code."""
        ...

    def send_notification(self, channel: str, recipient: str, body: str) -> bool:
        """Send a transactional notification."""
        ...


@dataclass(frozen=True)
class IdentityVerificationResult:
    """Signatory or individual identity verification outcome."""

    verified: bool
    confidence: float
    details: str
    reference_id: str


@runtime_checkable
class IdentityVerifier(Protocol):
    """Interface for verifying identity of institution signatories and authorised officers."""

    def verify_signatory(
        self,
        name: str,
        signatory_ref: str,
        institution_aicte_id: str,
    ) -> IdentityVerificationResult:
        """Verify the legal authority of an institutional signatory."""
        ...

    def verify_identity(self, name: str, id_reference: str) -> IdentityVerificationResult:
        """Verify identity of an individual using reference credentials."""
        ...


@runtime_checkable
class Storage(Protocol):
    """Interface for storing documents, justifications, and verification artifacts."""

    def save(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Save file content and return storage reference/path."""
        ...

    def get(self, path: str) -> bytes:
        """Retrieve file content bytes by reference."""
        ...

    def exists(self, path: str) -> bool:
        """Check if file exists in storage."""
        ...

    def delete(self, path: str) -> bool:
        """Delete file from storage."""
        ...

    def get_url(self, path: str) -> str:
        """Get downloadable URL or URI for the stored file."""
        ...
