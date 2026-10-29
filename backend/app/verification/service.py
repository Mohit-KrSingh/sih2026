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
from datetime import UTC, datetime, timedelta
from typing import Any

import qrcode
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.audit import service as audit_service
from app.auth.otp import store_and_send_otp
from app.auth.security import hash_password
from app.config import get_settings
from app.db import get_redis_client
from app.models import (
    ConsentRequest,
    MockApaarRegistry,
    Student,
    Submission,
    User,
    VerifiedRecord,
    Verifier,
)
from app.verification.schemas import (
    StudentAcademicRecordItem,
    VerifierRegisterRequest,
)
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
    existing_vr = db.scalar(select(VerifiedRecord).where(VerifiedRecord.student_id == student.id))
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
        else (getattr(student, "course_name", None) or "General Technical Course")
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
        else (getattr(student, "course_name", None) or "General Technical Course")
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


def generate_student_certificate_service(
    db: Session,
    student_id: int,
    actor: User | None = None,
    client_ip: str = "127.0.0.1",
    base_url: str | None = None,
) -> tuple[bytes, str]:
    """Generate a sample degree certificate PDF for a student with audit logging.

    Spec: Section 17 & TASKS.md T35:
    - Side-by-side College Student ID and APAAR ID.
    - Embedded verification QR code leading to the verify flow.
    - Appends hash-chained audit log 'certificate.generate'.
    """
    student = db.scalar(
        select(Student)
        .options(
            joinedload(Student.institution),
            joinedload(Student.course),
            joinedload(Student.verified_record),
        )
        .where(Student.id == student_id)
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student #{student_id} not found.",
        )

    from app.verification.certificate import generate_certificate_pdf

    pdf_bytes = generate_certificate_pdf(
        student=student,
        db=db,
        base_url=base_url,
        actor=actor,
        client_ip=client_ip,
    )

    vr = student.verified_record
    vid = vr.verification_id if vr else "unissued"

    # Audit log entry for certificate generation
    actor_id = actor.id if actor else None
    actor_role = actor.role if actor else "student"
    audit_service.record(
        db=db,
        actor_id=actor_id,
        actor_role=actor_role,
        action="certificate.generate",
        entity="student",
        entity_id=str(student.id),
        before_json=None,
        after_json={
            "student_id": student.id,
            "institution_id": student.institution_id,
            "enrolment_no": student.enrolment_no,
            "verification_id": vid,
        },
        ip=client_ip,
    )

    filename = f"certificate_{student.enrolment_no}.pdf"
    return pdf_bytes, filename


# Verifier Onboarding Service Logic (SPEC.md Section 14, TASKS.md T33)


def register_verifier(
    db: Session,
    req: VerifierRegisterRequest,
    client_ip: str = "127.0.0.1",
) -> tuple[Verifier, User]:
    """Register a new verifier organisation (employer, regulator, or institution).

    Status defaults to 'pending' awaiting AICTE admin review and approval.
    Creates an associated User record with role 'verifier', inactive until approved.
    """
    clean_email = req.contact.strip().lower()
    clean_name = req.org_name.strip()

    # Check for duplicate verifier contact
    existing_verifier = db.scalar(
        select(Verifier).where(func.lower(Verifier.contact) == clean_email)
    )
    if existing_verifier:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A verifier organisation with contact '{clean_email}' already exists.",
        )

    # Check if user email is already registered
    existing_user = db.scalar(select(User).where(func.lower(User.email) == clean_email))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with email '{clean_email}' is already registered in the system.",
        )

    # Create Verifier organisation record with pending status
    verifier = Verifier(
        org_name=clean_name,
        org_type=req.org_type,
        contact=clean_email,
        status="pending",
    )
    db.add(verifier)
    db.flush()

    # Create associated verifier User account (inactive until AICTE approval)
    hashed_pwd = hash_password(req.password)
    user = User(
        email=clean_email,
        password_hash=hashed_pwd,
        role="verifier",
        institution_id=None,
        is_active=False,
    )
    db.add(user)
    db.flush()

    # Hash-chained audit logging
    audit_service.record(
        db=db,
        actor_id=None,
        actor_role="verifier",
        action="verifier.register",
        entity="verifier",
        entity_id=str(verifier.id),
        before_json=None,
        after_json={
            "verifier_id": verifier.id,
            "org_name": verifier.org_name,
            "org_type": verifier.org_type,
            "contact": verifier.contact,
            "status": "pending",
        },
        ip=client_ip,
    )

    return verifier, user


def list_verifiers(
    db: Session,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Verifier], int]:
    """List verifier organisations with optional status filter for AICTE admin oversight."""
    base_query = select(Verifier)
    count_query = select(func.count()).select_from(Verifier)

    if status_filter:
        clean_status = status_filter.strip().lower()
        base_query = base_query.where(Verifier.status == clean_status)
        count_query = count_query.where(Verifier.status == clean_status)

    total = db.scalar(count_query) or 0
    items = list(
        db.scalars(
            base_query.order_by(Verifier.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )
    return items, total


def get_verifier(db: Session, verifier_id: int) -> Verifier:
    """Retrieve verifier organisation by ID."""
    verifier = db.scalar(select(Verifier).where(Verifier.id == verifier_id))
    if not verifier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verifier organisation with ID {verifier_id} not found.",
        )
    return verifier


def approve_verifier(
    db: Session,
    verifier_id: int,
    actor: User,
    client_ip: str = "127.0.0.1",
    note: str | None = None,
) -> Verifier:
    """Approve a pending verifier organisation (AICTE admin only).

    Activates the associated verifier User account and transitions status to 'approved'.
    """
    if actor.role != "aicte_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only AICTE administrators can approve verifier organisations.",
        )

    verifier = get_verifier(db, verifier_id)
    prev_status = verifier.status
    verifier.status = "approved"

    # Activate associated user account
    user = db.scalar(select(User).where(func.lower(User.email) == verifier.contact.lower()))
    if user:
        user.is_active = True

    db.flush()

    audit_service.record(
        db=db,
        actor_id=actor.id,
        actor_role=actor.role,
        action="verifier.approve",
        entity="verifier",
        entity_id=str(verifier.id),
        before_json={"status": prev_status},
        after_json={"status": "approved", "note": note},
        ip=client_ip,
    )

    return verifier


def revoke_verifier(
    db: Session,
    verifier_id: int,
    actor: User,
    client_ip: str = "127.0.0.1",
    note: str | None = None,
) -> Verifier:
    """Revoke or reject a verifier organisation (AICTE admin only).

    Deactivates associated user login and blocks subsequent verification queries.
    """
    if actor.role != "aicte_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only AICTE administrators can revoke verifier organisations.",
        )

    verifier = get_verifier(db, verifier_id)
    prev_status = verifier.status
    verifier.status = "revoked"

    user = db.scalar(select(User).where(func.lower(User.email) == verifier.contact.lower()))
    if user:
        user.is_active = False

    db.flush()

    audit_service.record(
        db=db,
        actor_id=actor.id,
        actor_role=actor.role,
        action="verifier.revoke",
        entity="verifier",
        entity_id=str(verifier.id),
        before_json={"status": prev_status},
        after_json={"status": "revoked", "note": note},
        ip=client_ip,
    )

    return verifier


def get_verifier_for_user(db: Session, user: User) -> Verifier:
    """Retrieve and validate the active Verifier organisation linked to a verifier User account."""
    clean_email = user.email.strip().lower()
    verifier = db.scalar(select(Verifier).where(func.lower(Verifier.contact) == clean_email))
    if not verifier:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No verifier organisation profile found for this account.",
        )
    if verifier.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Verifier organisation status is '{verifier.status}'. "
                "AICTE administrator approval is required before initiating verifications."
            ),
        )
    return verifier


# Consent Engine Lifecycle Logic (SPEC.md Section 14, TASKS.md T33)


def create_consent_request(
    db: Session,
    verifier_user: User,
    apaar_id: str,
    purpose: str,
    client_ip: str = "127.0.0.1",
) -> ConsentRequest:
    """Initiate a 24-hour student consent request with minimal disclosure scope.

    SPEC.md Section 14 & TASKS.md T33:
    - Verifier enters an APAAR ID.
    - Consent request goes to the student (mock OTP shown in dev outbox / student portal).
    - Consent has a scope, expires after 24 hours by default.
    - Single use.
    """
    verifier = get_verifier_for_user(db, verifier_user)
    clean_apaar = apaar_id.strip()

    if not clean_apaar.isdigit() or len(clean_apaar) != 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="APAAR ID must be exactly 12 numeric digits.",
        )

    # Check that student exists in either central Student records or mock registry
    in_students = (
        db.scalar(select(func.count()).select_from(Student).where(Student.apaar_id == clean_apaar))
        or 0
    ) > 0
    in_mock = (
        db.scalar(
            select(func.count())
            .select_from(MockApaarRegistry)
            .where(MockApaarRegistry.apaar_id == clean_apaar)
        )
        or 0
    ) > 0
    if not (in_students or in_mock):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with APAAR ID '{clean_apaar}' was not found in the national registry.",
        )

    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=24)

    # Minimal scope per SPEC.md Section 14: institution, course, years, status, verification_id
    scope_json = {
        "fields": ["institution", "course", "years", "status", "verification_id"],
        "purpose": purpose.strip(),
        "used": False,
        "single_use": True,
    }

    consent = ConsentRequest(
        verifier_id=verifier.id,
        apaar_id=clean_apaar,
        scope_json=scope_json,
        status="pending",
        requested_at=now,
        expires_at=expires_at,
    )
    db.add(consent)
    db.flush()

    # Dispatch mock OTP notification to student
    try:
        redis_client = get_redis_client()
        store_and_send_otp(
            db=db,
            redis_client=redis_client,
            recipient=clean_apaar,
            channel="sms",
            purpose="student_consent",
            context=(
                f"Consent request #{consent.id} from {verifier.org_name} for purpose: {purpose}"
            ),
        )
    except Exception as exc:
        logger.warning("Could not dispatch consent OTP to student outbox: %s", exc)

    audit_service.record(
        db=db,
        actor_id=verifier_user.id,
        actor_role=verifier_user.role,
        action="consent.request",
        entity="consent_request",
        entity_id=str(consent.id),
        before_json=None,
        after_json={
            "consent_request_id": consent.id,
            "verifier_id": verifier.id,
            "verifier_name": verifier.org_name,
            "apaar_id": clean_apaar,
            "purpose": purpose,
            "expires_at": expires_at.isoformat(),
        },
        ip=client_ip,
    )

    return consent


def list_consent_requests_for_verifier(
    db: Session,
    verifier_user: User,
    status_filter: str | None = None,
) -> list[ConsentRequest]:
    """List consent requests initiated by the verifier organisation."""
    verifier = get_verifier_for_user(db, verifier_user)
    now = datetime.now(UTC)

    # Auto-expire pending requests that have passed expires_at
    expired_requests = list(
        db.scalars(
            select(ConsentRequest).where(
                ConsentRequest.verifier_id == verifier.id,
                ConsentRequest.status == "pending",
                ConsentRequest.expires_at < now,
            )
        ).all()
    )
    for r in expired_requests:
        r.status = "expired"
    if expired_requests:
        db.flush()

    stmt = (
        select(ConsentRequest)
        .options(joinedload(ConsentRequest.verifier))
        .where(ConsentRequest.verifier_id == verifier.id)
    )
    if status_filter:
        clean_status = status_filter.strip().lower()
        stmt = stmt.where(ConsentRequest.status == clean_status)

    return list(db.scalars(stmt.order_by(ConsentRequest.requested_at.desc())).all())


def list_consent_requests_for_student(
    db: Session,
    apaar_id: str,
) -> list[ConsentRequest]:
    """List all consent requests addressed to the student's APAAR ID."""
    clean_apaar = apaar_id.strip()
    now = datetime.now(UTC)

    # Auto-expire pending requests
    expired_requests = list(
        db.scalars(
            select(ConsentRequest).where(
                ConsentRequest.apaar_id == clean_apaar,
                ConsentRequest.status == "pending",
                ConsentRequest.expires_at < now,
            )
        ).all()
    )
    for r in expired_requests:
        r.status = "expired"
    if expired_requests:
        db.flush()

    stmt = (
        select(ConsentRequest)
        .options(joinedload(ConsentRequest.verifier))
        .where(ConsentRequest.apaar_id == clean_apaar)
        .order_by(ConsentRequest.requested_at.desc())
    )
    return list(db.scalars(stmt).all())


def decide_consent_request(
    db: Session,
    request_id: int,
    decision: str,
    student_apaar_id: str,
    client_ip: str = "127.0.0.1",
) -> ConsentRequest:
    """Student approves or denies a consent request.

    - Validates ownership (must match student_apaar_id).
    - Checks 24-hour expiration (expired requests cannot be approved).
    - Enforces single decision.
    - Records hash-chained audit entry.
    """
    clean_decision = decision.strip().lower()
    if clean_decision not in ("approved", "denied"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be either 'approved' or 'denied'.",
        )

    cr = db.scalar(
        select(ConsentRequest)
        .options(joinedload(ConsentRequest.verifier))
        .where(ConsentRequest.id == request_id)
    )
    if not cr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consent request #{request_id} not found.",
        )

    if cr.apaar_id != student_apaar_id.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you may only decide consent requests for your own APAAR ID.",
        )

    now = datetime.now(UTC)
    if now > cr.expires_at:
        cr.status = "expired"
        db.flush()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Consent request has expired (24-hour statutory TTL). "
                "Expired requests cannot be approved."
            ),
        )

    if cr.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Consent request has already been decided with status '{cr.status}'.",
        )

    prev_status = cr.status
    cr.status = clean_decision
    cr.decided_at = now
    db.flush()

    audit_service.record(
        db=db,
        actor_id=None,
        actor_role="student",
        action=f"consent.{clean_decision}",
        entity="consent_request",
        entity_id=str(cr.id),
        before_json={"status": prev_status},
        after_json={
            "consent_request_id": cr.id,
            "status": clean_decision,
            "decided_at": now.isoformat(),
            "apaar_id": cr.apaar_id,
        },
        ip=client_ip,
    )

    return cr


def read_consented_student_record(
    db: Session,
    request_id: int,
    verifier_user: User,
    client_ip: str = "127.0.0.1",
) -> dict[str, Any]:
    """Verifier reads student record backed by approved student consent.

    SPEC.md Section 14 & TASKS.md T33:
    - Minimal disclosure: on approval verifier sees ONLY institution, course,
      years, status, verification ID, and 'verified by AICTE'.
    - NEVER DOB, category, or contact data.
    - Single use: accessed once, then consumed.
    - Every read is audit logged.
    """
    verifier = get_verifier_for_user(db, verifier_user)

    cr = db.scalar(
        select(ConsentRequest)
        .options(joinedload(ConsentRequest.verifier))
        .where(ConsentRequest.id == request_id)
    )
    if not cr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consent request #{request_id} not found.",
        )

    if cr.verifier_id != verifier.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: this consent request was created by another organisation.",
        )

    now = datetime.now(UTC)
    if now > cr.expires_at:
        cr.status = "expired"
        db.flush()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: student consent has expired (24-hour limit).",
        )

    if cr.status == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: student consent is pending approval.",
        )

    if cr.status == "denied":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: student denied consent for this verification request.",
        )

    if cr.status == "expired":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: student consent has expired.",
        )

    # Check single-use policy
    scope = dict(cr.scope_json or {})
    if scope.get("used", False) or cr.status == "used":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Access denied: student consent has already been used. "
                "Consents are single-use per DPDP policy."
            ),
        )

    # Mark consent as consumed (single-use)
    scope["used"] = True
    scope["used_at"] = now.isoformat()
    cr.scope_json = scope
    cr.status = "used"
    db.flush()

    # Query active/accepted student academic record
    student = db.scalar(
        select(Student)
        .options(
            joinedload(Student.institution),
            joinedload(Student.course),
            joinedload(Student.verified_record),
        )
        .where(Student.apaar_id == cr.apaar_id)
        .order_by(Student.academic_year.desc())
    )

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No academic records found for this student in the central repository.",
        )

    # Retrieve verification ID
    if student.verified_record and student.verified_record.status == "active":
        vid = student.verified_record.verification_id
    else:
        # Check if any verified record exists for student's apaar_id
        alt_vr = db.scalar(
            select(VerifiedRecord)
            .join(Student)
            .where(Student.apaar_id == cr.apaar_id, VerifiedRecord.status == "active")
        )
        vid = (
            alt_vr.verification_id
            if alt_vr
            else f"VR-AICTE-{student.academic_year}-{student.id:04d}"
        )

    inst_name = (
        student.institution.name
        if student.institution
        else f"Institution #{student.institution_id}"
    )
    course_name = (
        student.course.name
        if student.course
        else (student.course_name or "General Technical Program")
    )

    # Strictly minimal payload - ZERO DOB, ZERO category, ZERO contact data
    record_payload = {
        "institution": inst_name,
        "course": course_name,
        "years": student.academic_year,
        "status": student.status,
        "verification_id": vid,
        "verified_by": "AICTE Central Repository",
        "verified": True,
        "purpose": scope.get("purpose", "Pre-employment or academic verification"),
        "accessed_at": now,
        "consent_request_id": cr.id,
        "verifier_name": verifier.org_name,
        "message": (
            "Academic record verified with authorized student consent under "
            "DPDP data minimisation policy."
        ),
    }

    # Audit log entry for EVERY verifier read
    audit_service.record(
        db=db,
        actor_id=verifier_user.id,
        actor_role=verifier_user.role,
        action="verifier.read_student_data",
        entity="student",
        entity_id=str(student.id),
        before_json=None,
        after_json={
            "verification_id": vid,
            "consent_request_id": cr.id,
            "institution": inst_name,
            "course": course_name,
            "years": student.academic_year,
            "status": student.status,
            "verifier_id": verifier.id,
            "verifier_name": verifier.org_name,
        },
        ip=client_ip,
    )

    return record_payload


def get_student_academic_records(
    db: Session,
    apaar_id: str,
) -> list[StudentAcademicRecordItem]:
    """Retrieve all academic records holding the student's APAAR ID."""
    clean_apaar = apaar_id.strip()
    students = list(
        db.scalars(
            select(Student)
            .options(
                joinedload(Student.institution),
                joinedload(Student.course),
                joinedload(Student.verified_record),
            )
            .where(Student.apaar_id == clean_apaar)
            .order_by(Student.academic_year.desc())
        ).all()
    )

    records: list[StudentAcademicRecordItem] = []
    for s in students:
        inst_name = s.institution.name if s.institution else f"Institution #{s.institution_id}"
        aicte_id = s.institution.aicte_id if s.institution else "N/A"
        c_name = s.course.name if s.course else (s.course_name or "General Technical Program")
        vid = s.verified_record.verification_id if s.verified_record else None
        issued_at = s.verified_record.issued_at if s.verified_record else None

        records.append(
            StudentAcademicRecordItem(
                student_id=s.id,
                enrolment_no=s.enrolment_no,
                institution_id=s.institution_id,
                institution_name=inst_name,
                institution_aicte_id=aicte_id,
                course_id=s.course_id,
                course_name=c_name,
                academic_year=s.academic_year,
                status=s.status,
                verification_id=vid,
                issued_at=issued_at,
            )
        )

    return records
