"""Verification service: credential issuance, Ed25519 signing, verification, and revocation.

SPEC.md section 14:
- Signed proof: each accepted or clean record gets a verification_id and an Ed25519
  signature over a canonical payload (verification_id, apaar_id hash, institution,
  course, years, status, issued_at).
- QR code encodes a link to `/verify?vid=...`, containing no personal data.
- Tampering with any signed field must fail verification.
- Support revocation.
- Every state change is audit logged.
"""

from __future__ import annotations

import io
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import qrcode
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.audit import service as audit_service
from app.config import get_settings
from app.models import Student, Submission, User, VerifiedRecord
from app.verification.signing import (
    build_canonical_payload,
    format_canonical_issued_at,
    sign_payload,
    verify_signature,
)

logger = logging.getLogger(__name__)


def generate_verification_id(academic_year: str, prefix: str = "VR") -> str:
    """Generate a clean, professional verification identifier (VID).

    Format: VR-{year}-{token12}
    Example: VR-2026-9FA8B1C2D3E4
    """
    clean_year = academic_year.replace("/", "-")[:4]
    token = uuid.uuid4().hex[:12].upper()
    return f"{prefix}-{clean_year}-{token}"


def issue_verified_record(
    db: Session,
    student: Student,
    status_override: str | None = None,
    actor: User | None = None,
    client_ip: str = "127.0.0.1",
) -> VerifiedRecord:
    """Issue a cryptographically signed verifiable credential for an accepted student record.

    - Updates student status to 'verified' or 'verified_with_exception'.
    - Generates unique verification_id.
    - Signs canonical payload with Ed25519.
    - Persists VerifiedRecord.
    - Appends to hash-chained audit log.
    """
    # Check if student already has a verified record
    existing_vr = db.scalar(
        select(VerifiedRecord).where(VerifiedRecord.student_id == student.id)
    )
    if existing_vr and existing_vr.status == "active":
        return existing_vr

    # Determine student status (preserves existing status unless override provided)
    if status_override:
        target_status = status_override
        student.status = target_status
    elif student.status == "flagged":
        target_status = "verified_with_exception"
        student.status = target_status
    else:
        target_status = student.status or "submitted"

    # Prepare canonical data components
    inst_name = (
        student.institution.name
        if student.institution
        else f"Institution #{student.institution_id}"
    )
    course_name = (
        student.course.name
        if student.course
        else (student.course_name or "General Technical Course")
    )
    issued_at = datetime.now(UTC)
    vid = generate_verification_id(student.academic_year)

    # Build canonical payload and sign with Ed25519
    payload = build_canonical_payload(
        verification_id=vid,
        apaar_id=student.apaar_id,
        institution=inst_name,
        course=course_name,
        years=student.academic_year,
        status=target_status,
        issued_at=issued_at,
    )
    signature_hex = sign_payload(payload)

    if existing_vr:
        # Re-issuing over revoked or previous record
        existing_vr.verification_id = vid
        existing_vr.signature = signature_hex
        existing_vr.issued_at = issued_at
        existing_vr.status = "active"
        vr = existing_vr
    else:
        vr = VerifiedRecord(
            student_id=student.id,
            verification_id=vid,
            signature=signature_hex,
            issued_at=issued_at,
            status="active",
        )
        db.add(vr)

    db.flush()

    # Record issuance in audit log
    actor_id = actor.id if actor else None
    actor_role = actor.role if actor else "system"
    audit_service.record(
        db=db,
        actor_id=actor_id,
        actor_role=actor_role,
        action="verification.issue",
        entity="verified_record",
        entity_id=str(vr.id),
        before_json=None,
        after_json={
            "verification_id": vid,
            "student_id": student.id,
            "institution_id": student.institution_id,
            "academic_year": student.academic_year,
            "status": "active",
            "student_status": target_status,
        },
        ip=client_ip,
    )

    return vr


def issue_verified_records_for_submission(
    db: Session,
    submission: Submission,
    actor: User | None = None,
    client_ip: str = "127.0.0.1",
) -> list[VerifiedRecord]:
    """Issue verifiable credentials for all eligible active students in a submission.

    Invoked upon:
    1. Clean submission (SubmissionState.SUBMITTED)
    2. Final AICTE acceptance (SubmissionState.ACCEPTED)
    """
    students = list(
        db.scalars(
            select(Student)
            .options(joinedload(Student.institution), joinedload(Student.course))
            .where(
                Student.institution_id == submission.institution_id,
                Student.academic_year == submission.academic_year,
                Student.status.notin_(["withdrawn", "transferred"]),
            )
        ).all()
    )

    issued_records: list[VerifiedRecord] = []
    for student in students:
        vr = issue_verified_record(
            db=db,
            student=student,
            actor=actor,
            client_ip=client_ip,
        )
        issued_records.append(vr)

    db.flush()
    return issued_records


def revoke_verified_record(
    db: Session,
    verification_id: str,
    reason: str,
    actor: User,
    client_ip: str = "127.0.0.1",
) -> VerifiedRecord:
    """Revoke an active verifiable credential.

    - Verifies permissions (AICTE officer/admin or college_admin with IDOR scoping).
    - Transitions VerifiedRecord status to 'revoked'.
    - Records tamper-evident audit entry.
    """
    clean_reason = reason.strip() if reason else ""
    if len(clean_reason) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A substantive revocation reason is required (minimum 3 characters).",
        )

    vr = db.scalar(
        select(VerifiedRecord)
        .options(joinedload(VerifiedRecord.student).joinedload(Student.institution))
        .where(VerifiedRecord.verification_id == verification_id.strip())
    )
    if not vr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification record with ID '{verification_id}' not found.",
        )

    # Scoping check for college_admin (IDOR protection)
    if actor.role == "college_admin":
        if vr.student.institution_id != actor.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Institutions may only revoke credentials issued to their own students.",
            )

    if vr.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification record is already revoked.",
        )

    prev_status = vr.status
    vr.status = "revoked"
    db.flush()

    # Append to hash-chained audit log
    audit_service.record(
        db=db,
        actor_id=actor.id,
        actor_role=actor.role,
        action="verification.revoke",
        entity="verified_record",
        entity_id=str(vr.id),
        before_json={"status": prev_status, "verification_id": vr.verification_id},
        after_json={
            "status": "revoked",
            "verification_id": vr.verification_id,
            "reason": clean_reason,
            "revoked_by": actor.id,
        },
        ip=client_ip,
    )

    return vr


def verify_credential_by_id(db: Session, verification_id: str) -> dict[str, Any]:
    """Verify an academic credential by its Verification ID.

    Publicly callable and rate-limited.
    SPEC.md Section 14:
    - On approval/verification the verifier sees only: institution, course, years,
      status, verification ID, and "verified by AICTE".
    - Never DOB, category, or contact data.
    - Tampering with any signed field causes verification to fail.
    """
    clean_vid = str(verification_id).strip()
    if not clean_vid:
        return {
            "verified": False,
            "status": "invalid_query",
            "message": "Verification ID cannot be empty.",
        }

    vr = db.scalar(
        select(VerifiedRecord)
        .options(
            joinedload(VerifiedRecord.student).joinedload(Student.institution),
            joinedload(VerifiedRecord.student).joinedload(Student.course),
        )
        .where(VerifiedRecord.verification_id == clean_vid)
    )

    if not vr:
        return {
            "verified": False,
            "status": "not_found",
            "verification_id": clean_vid,
            "message": "Verification record not found in AICTE Central Repository.",
        }

    if vr.status == "revoked":
        return {
            "verified": False,
            "status": "revoked",
            "verification_id": clean_vid,
            "message": "This credential has been revoked by AICTE or the issuing institution.",
            "issued_at": format_canonical_issued_at(vr.issued_at),
        }

    student = vr.student
    inst_name = (
        student.institution.name
        if student.institution
        else f"Institution #{student.institution_id}"
    )
    course_name = (
        student.course.name
        if student.course
        else (student.course_name or "General Technical Course")
    )

    # Reconstruct canonical payload from current DB state to detect tampering
    canonical_payload = build_canonical_payload(
        verification_id=vr.verification_id,
        apaar_id=student.apaar_id,
        institution=inst_name,
        course=course_name,
        years=student.academic_year,
        status=student.status,
        issued_at=vr.issued_at,
    )

    # Cryptographically verify the Ed25519 signature
    is_valid = verify_signature(canonical_payload, vr.signature)
    if not is_valid:
        return {
            "verified": False,
            "status": "tampered",
            "verification_id": clean_vid,
            "message": (
                "Cryptographic signature verification failed: record has been altered or "
                "tampered with since issuance."
            ),
        }

    # Valid response: strictly minimal fields, no PII (DPDP compliance)
    return {
        "verified": True,
        "status": "active",
        "verification_id": vr.verification_id,
        "message": "Record cryptographically verified by AICTE Central Repository.",
        "verified_by": "AICTE Central Repository",
        "institution": inst_name,
        "course": course_name,
        "years": student.academic_year,
        "student_status": student.status,
        "issued_at": format_canonical_issued_at(vr.issued_at),
        "signature_preview": f"{vr.signature[:32]}...",
    }


def generate_qr_code_png(verification_id: str, base_url: str | None = None) -> bytes:
    """Generate a high-contrast QR code PNG encoding the verification URL.

    SPEC.md Section 14:
    - QR code encodes a link to `/verify?vid=...`, containing no personal data.
    """
    settings = get_settings()
    root_url = (base_url or settings.FRONTEND_URL).rstrip("/")
    verification_url = f"{root_url}/verify?vid={verification_id.strip()}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(verification_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
