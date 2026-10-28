"""Verification module: signing, verification IDs, QR code generation, and verification API."""

from app.verification.certificate import generate_certificate_pdf
from app.verification.router import router
from app.verification.service import (
    generate_qr_code_png,
    generate_student_certificate_service,
    generate_verification_id,
    issue_verified_record,
    issue_verified_records_for_submission,
    revoke_verified_record,
    verify_credential_by_id,
)
from app.verification.signing import (
    build_canonical_payload,
    format_canonical_issued_at,
    get_public_key_hex,
    get_signing_key,
    get_verify_key,
    serialize_canonical_payload,
    sign_payload,
    verify_signature,
)

__all__ = [
    "build_canonical_payload",
    "format_canonical_issued_at",
    "generate_certificate_pdf",
    "generate_qr_code_png",
    "generate_student_certificate_service",
    "generate_verification_id",
    "get_public_key_hex",
    "get_signing_key",
    "get_verify_key",
    "issue_verified_record",
    "issue_verified_records_for_submission",
    "revoke_verified_record",
    "router",
    "serialize_canonical_payload",
    "sign_payload",
    "verify_credential_by_id",
    "verify_signature",
]
