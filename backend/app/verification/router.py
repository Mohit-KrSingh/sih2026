"""Verification API router: verification search, QR codes, public key, revocation,"""

import io
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user, oauth2_scheme, require_roles
from app.auth.otp import store_and_send_otp, verify_otp
from app.auth.rate_limiter import RateLimiter
from app.auth.security import decode_token
from app.config import get_settings
from app.db import get_db, get_redis_client
from app.models import ConsentRequest, MockApaarRegistry, Student, User, VerifiedRecord
from app.verification.schemas import (
    ConsentDecisionRequest,
    ConsentedStudentRecordResponse,
    ConsentRequestCreate,
    ConsentRequestListResponse,
    ConsentRequestResponse,
    StudentOtpRequest,
    StudentOtpVerifyRequest,
    StudentRecordsListResponse,
    StudentTokenResponse,
    VerifierListResponse,
    VerifierRegisterRequest,
    VerifierResponse,
    VerifierStatusUpdateRequest,
)
from app.verification.service import (
    approve_verifier,
    create_consent_request,
    decide_consent_request,
    generate_qr_code_png,
    generate_student_certificate_service,
    get_student_academic_records,
    get_verifier,
    get_verifier_for_user,
    list_consent_requests_for_student,
    list_consent_requests_for_verifier,
    list_verifiers,
    read_consented_student_record,
    register_verifier,
    revoke_verified_record,
    revoke_verifier,
    verify_credential_by_id,
)
from app.verification.signing import (
    format_canonical_issued_at,
    get_public_key_hex,
)

router = APIRouter(prefix="/verification", tags=["verification"])
settings = get_settings()

verify_rate_limiter = RateLimiter(
    times=settings.RATE_LIMIT_VERIFY_PER_MINUTE,
    seconds=60,
    label="verify",
)


# Helpers


def create_student_token(apaar_id: str, student_name: str | None = None) -> str:
    """Issue a 24-hour signed JWT session token for student portal authentication."""
    now = datetime.now(UTC)
    expire = now + timedelta(hours=24)
    payload = {
        "sub": f"student:{apaar_id}",
        "apaar_id": apaar_id,
        "name": student_name,
        "role": "student",
        "type": "student_access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def get_current_student(
    token: str = Depends(oauth2_scheme),
) -> str:
    """Validate student session token and return the authenticated 12-digit APAAR ID."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate student credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Student session has expired. Please log in again with OTP.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.PyJWTError:
        raise credentials_exception from None

    if payload.get("role") != "student" or payload.get("type") != "student_access":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: valid student portal token required",
        )

    apaar_id = payload.get("apaar_id")
    if not apaar_id:
        raise credentials_exception

    return str(apaar_id)


def _map_consent_response(cr: ConsentRequest) -> ConsentRequestResponse:
    """Map internal ConsentRequest ORM model to API response contract."""
    now = datetime.now(UTC)
    scope = cr.scope_json or {}
    fields = scope.get("fields", ["institution", "course", "years", "status", "verification_id"])
    purpose = scope.get("purpose", "Pre-employment or academic verification")
    is_used = scope.get("used", False) or cr.status == "used"
    is_expired = now > cr.expires_at and cr.status not in ("approved", "used")

    verifier_name = cr.verifier.org_name if cr.verifier else f"Verifier #{cr.verifier_id}"
    verifier_type = cr.verifier.org_type if cr.verifier else "employer"

    status_val = "expired" if (is_expired and cr.status == "pending") else cr.status

    return ConsentRequestResponse(
        id=cr.id,
        verifier_id=cr.verifier_id,
        verifier_name=verifier_name,
        verifier_type=verifier_type,
        apaar_id=cr.apaar_id,
        status=status_val,
        purpose=purpose,
        scope_fields=fields,
        requested_at=cr.requested_at,
        decided_at=cr.decided_at,
        expires_at=cr.expires_at,
        is_expired=is_expired,
        is_used=is_used,
    )


# Existing Models (T32)


class RevokeRecordRequest(BaseModel):
    reason: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Justification or statutory directive for credential revocation",
        examples=["Student withdrew from academic program prior to term completion"],
    )


class PublicRecordResponse(BaseModel):
    verification_id: str
    status: str
    issued_at: str
    signature: str
    verified: bool
    issued_by: str = "AICTE Central Repository"


# Public Verification Endpoints (T32)


@router.get(
    "/verify",
    dependencies=[Depends(verify_rate_limiter)],
)
def verify_record_query(
    vid: str | None = Query(None, description="Verification ID from credential QR code"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Public verification lookup endpoint."""
    if not vid:
        return {
            "status": "ready",
            "message": "Verification service is online. Provide a vid parameter to verify.",
            "verified": False,
        }

    return verify_credential_by_id(db=db, verification_id=vid)


@router.get(
    "/records/{verification_id}",
    dependencies=[Depends(verify_rate_limiter)],
    response_model=PublicRecordResponse,
)
def get_verification_record(
    verification_id: str,
    db: Session = Depends(get_db),
) -> PublicRecordResponse:
    """Public record status and cryptographic proof lookup."""
    clean_vid = verification_id.strip()
    if len(clean_vid) < 5:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification record not found",
        )

    vr = db.scalar(select(VerifiedRecord).where(VerifiedRecord.verification_id == clean_vid))
    if not vr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification record with ID '{clean_vid}' not found",
        )

    check_result = verify_credential_by_id(db=db, verification_id=clean_vid)
    is_valid = bool(check_result.get("verified", False))

    return PublicRecordResponse(
        verification_id=vr.verification_id,
        status=vr.status,
        issued_at=format_canonical_issued_at(vr.issued_at),
        signature=vr.signature,
        verified=is_valid and vr.status == "active",
        issued_by="AICTE Central Repository",
    )


@router.get(
    "/records/{verification_id}/qr",
    dependencies=[Depends(verify_rate_limiter)],
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "High-contrast QR code image PNG encoding the verification URL",
        }
    },
)
def get_verification_qr_code(
    verification_id: str,
    db: Session = Depends(get_db),
) -> Response:
    """Generate high-contrast QR code PNG encoding link to `/verify?vid={vid}`."""
    clean_vid = verification_id.strip()
    vr = db.scalar(select(VerifiedRecord.id).where(VerifiedRecord.verification_id == clean_vid))
    if not vr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification record with ID '{clean_vid}' not found",
        )

    png_bytes = generate_qr_code_png(verification_id=clean_vid)
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=3600",
            "Content-Disposition": f'inline; filename="qr_{clean_vid}.png"',
        },
    )


@router.get(
    "/public-key",
    dependencies=[Depends(verify_rate_limiter)],
)
def get_ed25519_public_key() -> dict[str, str]:
    """Expose the AICTE Ed25519 public key in hex for third-party offline verification."""
    return {
        "algorithm": "Ed25519-SHA512",
        "public_key_hex": get_public_key_hex(),
        "issuer": "AICTE Central Repository",
        "description": (
            "Public verification key for validating student academic record credentials "
            "issued under the Smart India Hackathon EduTrace platform."
        ),
    }


@router.post(
    "/records/{verification_id}/revoke",
    dependencies=[Depends(require_roles("aicte_admin", "aicte_officer", "college_admin"))],
)
def revoke_record_endpoint(
    verification_id: str,
    payload: RevokeRecordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Revoke an active student verification record."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    vr = revoke_verified_record(
        db=db,
        verification_id=verification_id,
        reason=payload.reason,
        actor=current_user,
        client_ip=client_ip,
    )
    db.commit()

    return {
        "status": "revoked",
        "verification_id": vr.verification_id,
        "reason": payload.reason,
        "revoked_at": format_canonical_issued_at(vr.updated_at),
        "revoked_by": current_user.email,
    }


@router.get(
    "/students/{student_id}",
    dependencies=[
        Depends(
            require_roles(
                "college_admin", "college_staff", "aicte_admin", "aicte_officer", "aicte_viewer"
            )
        )
    ],
)
def get_student_verification_details(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get verified credential details for a student."""
    student = db.scalar(
        select(Student)
        .options(joinedload(Student.institution), joinedload(Student.course))
        .where(Student.id == student_id)
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student #{student_id} not found.",
        )

    if current_user.role in ("college_admin", "college_staff", "college_viewer"):
        if student.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view verification details for this student.",
            )

    vr = db.scalar(select(VerifiedRecord).where(VerifiedRecord.student_id == student_id))

    if not vr:
        return {
            "student_id": student.id,
            "has_credential": False,
            "status": "unissued",
            "message": "Student record does not yet have an issued verification credential.",
        }

    qr_url = f"/api/v1/verification/records/{vr.verification_id}/qr"
    verify_url = f"/verify?vid={vr.verification_id}"

    return {
        "student_id": student.id,
        "has_credential": True,
        "verification_id": vr.verification_id,
        "status": vr.status,
        "issued_at": format_canonical_issued_at(vr.issued_at),
        "qr_code_url": qr_url,
        "verify_url": verify_url,
        "signature_preview": f"{vr.signature[:24]}...",
    }


@router.get(
    "/students/{student_id}/certificate",
    summary="Download sample degree certificate PDF with side-by-side College ID and APAAR ID",
    dependencies=[
        Depends(
            require_roles(
                "college_admin",
                "college_staff",
                "college_viewer",
                "aicte_admin",
                "aicte_officer",
            )
        )
    ],
)
def get_student_certificate_from_verification(
    student_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    download: bool = Query(False, description="Whether to trigger file download attachment"),
) -> StreamingResponse:
    """Institutional endpoint to generate and download sample degree certificate PDF."""
    student = db.scalar(select(Student).where(Student.id == student_id))
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student #{student_id} not found.",
        )

    # Institutional IDOR guard for college roles
    if current_user.role in ("college_admin", "college_staff", "college_viewer"):
        if student.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access certificates for this student.",
            )

    client_ip = request.client.host if request.client else "127.0.0.1"
    pdf_bytes, filename = generate_student_certificate_service(
        db=db,
        student_id=student.id,
        actor=current_user,
        client_ip=client_ip,
    )

    disposition = "attachment" if download else "inline"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


# Verifier Onboarding & AICTE Admin Review Endpoints (T33)


@router.post(
    "/verifiers/register",
    response_model=VerifierResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_rate_limiter)],
)
def register_verifier_endpoint(
    payload: VerifierRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> VerifierResponse:
    """Public registration for verifying organisations (employers, regulators, institutions).

    SPEC.md Section 14 & TASKS.md T33:
    - Verifier organisation registers; status defaults to 'pending'.
    - AICTE admin reviews and approves.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    verifier, _ = register_verifier(db=db, req=payload, client_ip=client_ip)
    db.commit()
    db.refresh(verifier)
    return VerifierResponse.model_validate(verifier)


@router.get(
    "/verifiers",
    response_model=VerifierListResponse,
    dependencies=[Depends(require_roles("aicte_admin", "aicte_officer"))],
)
def list_verifiers_endpoint(
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status (pending, approved, revoked)",
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> VerifierListResponse:
    """AICTE admin review queue for verifier organisation onboarding."""
    items, total = list_verifiers(db=db, status_filter=status_filter, limit=limit, offset=offset)
    return VerifierListResponse(
        items=[VerifierResponse.model_validate(v) for v in items],
        total=total,
    )


@router.get(
    "/verifiers/me",
    response_model=VerifierResponse,
    dependencies=[Depends(require_roles("verifier"))],
)
def get_my_verifier_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VerifierResponse:
    """Retrieve organisation profile for the authenticated verifier."""
    verifier = get_verifier_for_user(db=db, user=current_user)
    return VerifierResponse.model_validate(verifier)


@router.get(
    "/verifiers/{verifier_id}",
    response_model=VerifierResponse,
    dependencies=[Depends(require_roles("aicte_admin", "aicte_officer"))],
)
def get_verifier_endpoint(
    verifier_id: int,
    db: Session = Depends(get_db),
) -> VerifierResponse:
    """Retrieve verifier organisation details by ID."""
    verifier = get_verifier(db=db, verifier_id=verifier_id)
    return VerifierResponse.model_validate(verifier)


@router.patch(
    "/verifiers/{verifier_id}/approve",
    response_model=VerifierResponse,
    dependencies=[Depends(require_roles("aicte_admin"))],
)
def approve_verifier_endpoint(
    verifier_id: int,
    payload: VerifierStatusUpdateRequest | None = None,
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VerifierResponse:
    """AICTE admin approves a verifier organisation, activating its verification privileges."""
    client_ip = request.client.host if (request and request.client) else "127.0.0.1"
    note = payload.note if payload else None
    verifier = approve_verifier(
        db=db,
        verifier_id=verifier_id,
        actor=current_user,
        client_ip=client_ip,
        note=note,
    )
    db.commit()
    db.refresh(verifier)
    return VerifierResponse.model_validate(verifier)


@router.patch(
    "/verifiers/{verifier_id}/revoke",
    response_model=VerifierResponse,
    dependencies=[Depends(require_roles("aicte_admin"))],
)
def revoke_verifier_endpoint(
    verifier_id: int,
    payload: VerifierStatusUpdateRequest | None = None,
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VerifierResponse:
    """AICTE admin revokes a verifier organisation, immediately blocking query capabilities."""
    client_ip = request.client.host if (request and request.client) else "127.0.0.1"
    note = payload.note if payload else None
    verifier = revoke_verifier(
        db=db,
        verifier_id=verifier_id,
        actor=current_user,
        client_ip=client_ip,
        note=note,
    )
    db.commit()
    db.refresh(verifier)
    return VerifierResponse.model_validate(verifier)


# Verifier Consent Request & Record Access Endpoints (T33)


@router.post(
    "/consent-requests",
    response_model=ConsentRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("verifier")), Depends(verify_rate_limiter)],
)
def create_consent_request_endpoint(
    payload: ConsentRequestCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsentRequestResponse:
    """Verifier initiates a 24-hour student consent request with minimal disclosure scope."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    consent = create_consent_request(
        db=db,
        verifier_user=current_user,
        apaar_id=payload.apaar_id,
        purpose=payload.purpose,
        client_ip=client_ip,
    )
    db.commit()
    db.refresh(consent)
    return _map_consent_response(consent)


@router.get(
    "/consent-requests",
    response_model=ConsentRequestListResponse,
    dependencies=[Depends(require_roles("verifier"))],
)
def list_consent_requests_endpoint(
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status (pending, approved, denied, expired, used)",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsentRequestListResponse:
    """List all consent requests initiated by the authenticated verifier organisation."""
    requests = list_consent_requests_for_verifier(
        db=db,
        verifier_user=current_user,
        status_filter=status_filter,
    )
    return ConsentRequestListResponse(
        items=[_map_consent_response(r) for r in requests],
        total=len(requests),
    )


@router.get(
    "/consent-requests/{request_id}",
    response_model=ConsentRequestResponse,
    dependencies=[Depends(require_roles("verifier"))],
)
def get_consent_request_endpoint(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsentRequestResponse:
    """Get consent request status for verifier."""
    verifier = get_verifier_for_user(db=db, user=current_user)
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
            detail="Access forbidden: this consent request belongs to another organisation.",
        )
    return _map_consent_response(cr)


@router.get(
    "/consent-requests/{request_id}/record",
    response_model=ConsentedStudentRecordResponse,
    dependencies=[Depends(require_roles("verifier")), Depends(verify_rate_limiter)],
)
def read_consented_record_endpoint(
    request_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsentedStudentRecordResponse:
    """Verifier reads student record backed by approved student consent.

    SPEC.md Section 14 & TASKS.md T33:
    - Minimal disclosure: on approval verifier sees ONLY institution, course,
      years, status, verification ID, and 'verified by AICTE'.
    - NEVER DOB, category, or contact data.
    - Single use: accessed once, then consumed.
    - Every read is audit logged.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    data = read_consented_student_record(
        db=db,
        request_id=request_id,
        verifier_user=current_user,
        client_ip=client_ip,
    )
    db.commit()
    return ConsentedStudentRecordResponse.model_validate(data)


# Student Consent Portal Endpoints (T33)


@router.post(
    "/student/otp/send",
    dependencies=[Depends(verify_rate_limiter)],
)
def student_otp_send_endpoint(
    payload: StudentOtpRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Student portal login initiation: dispatches mock OTP to student contact.

    SPEC.md Section 14:
    - Student portal: identified by APAAR ID plus mock OTP shown in dev outbox.
    """
    clean_apaar = payload.apaar_id.strip()

    # Verify that APAAR ID exists in either central Student records or mock registry
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
            detail=f"No academic or registry records found for APAAR ID '{clean_apaar}'.",
        )

    redis_client = get_redis_client()
    result = store_and_send_otp(
        db=db,
        redis_client=redis_client,
        recipient=clean_apaar,
        channel="sms",
        purpose="student_auth",
        context="APAAR Student Consent Portal Authentication",
    )
    return {
        "status": "sent",
        "apaar_id": clean_apaar,
        "channel": result["channel"],
        "expires_in": result["expires_in"],
        "message": "OTP successfully dispatched to registered student contacts and dev outbox.",
    }


@router.post(
    "/student/otp/verify",
    response_model=StudentTokenResponse,
    dependencies=[Depends(verify_rate_limiter)],
)
def student_otp_verify_endpoint(
    payload: StudentOtpVerifyRequest,
    db: Session = Depends(get_db),
) -> StudentTokenResponse:
    """Verify student OTP and issue a signed session JWT for student portal actions."""
    clean_apaar = payload.apaar_id.strip()
    redis_client = get_redis_client()

    success, msg, _ = verify_otp(
        redis_client=redis_client,
        recipient=clean_apaar,
        purpose="student_auth",
        code=payload.otp.strip(),
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    # Determine student name from registry or student record
    student_name: str | None = None
    mock_reg = db.scalar(select(MockApaarRegistry).where(MockApaarRegistry.apaar_id == clean_apaar))
    if mock_reg:
        student_name = mock_reg.name
    else:
        st = db.scalar(select(Student).where(Student.apaar_id == clean_apaar))
        if st:
            student_name = st.name

    token = create_student_token(apaar_id=clean_apaar, student_name=student_name)
    return StudentTokenResponse(
        access_token=token,
        token_type="bearer",
        apaar_id=clean_apaar,
        student_name=student_name,
        expires_in_hours=24,
    )


@router.get(
    "/student/records",
    response_model=StudentRecordsListResponse,
)
def get_student_records_endpoint(
    student_apaar_id: str = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> StudentRecordsListResponse:
    """Student views all colleges/institutions holding their academic records."""
    records = get_student_academic_records(db=db, apaar_id=student_apaar_id)
    return StudentRecordsListResponse(
        apaar_id=student_apaar_id,
        records=records,
        total=len(records),
    )


@router.get(
    "/student/records/{student_id}/certificate",
    summary="Student portal endpoint to download degree certificate PDF",
)
def get_student_portal_certificate_endpoint(
    student_id: int,
    request: Request,
    student_apaar_id: str = Depends(get_current_student),
    db: Session = Depends(get_db),
    download: bool = Query(False, description="Whether to trigger file download attachment"),
) -> StreamingResponse:
    """Download degree certificate PDF from authenticated student session."""
    student = db.scalar(select(Student).where(Student.id == student_id))
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student #{student_id} not found.",
        )
    if student.apaar_id != student_apaar_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to download certificates for other students.",
        )

    client_ip = request.client.host if request.client else "127.0.0.1"
    pdf_bytes, filename = generate_student_certificate_service(
        db=db,
        student_id=student.id,
        actor=None,
        client_ip=client_ip,
    )

    disposition = "attachment" if download else "inline"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get(
    "/student/consent-requests",
    response_model=ConsentRequestListResponse,
)
def get_student_consent_requests_endpoint(
    student_apaar_id: str = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> ConsentRequestListResponse:
    """Student lists all pending, approved, denied, and expired consent requests."""
    requests = list_consent_requests_for_student(db=db, apaar_id=student_apaar_id)
    return ConsentRequestListResponse(
        items=[_map_consent_response(r) for r in requests],
        total=len(requests),
    )


@router.post(
    "/student/consent-requests/{request_id}/decide",
    response_model=ConsentRequestResponse,
)
def decide_student_consent_endpoint(
    request_id: int,
    payload: ConsentDecisionRequest,
    request: Request,
    student_apaar_id: str = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> ConsentRequestResponse:
    """Student approves or denies a consent request with 24-hour statutory TTL."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    cr = decide_consent_request(
        db=db,
        request_id=request_id,
        decision=payload.decision,
        student_apaar_id=student_apaar_id,
        client_ip=client_ip,
    )
    db.commit()
    db.refresh(cr)
    return _map_consent_response(cr)
