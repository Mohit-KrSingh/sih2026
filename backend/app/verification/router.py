"""Verification API router: verification search, QR codes, public key, and revocation.

SPEC.md section 14 & 16, TASKS.md T32:
- Public rate-limited verification endpoint: `/api/v1/verification/verify?vid=...`.
- Public rate-limited record proof lookup: `/api/v1/verification/records/{vid}`.
- Public rate-limited QR PNG generator: `/api/v1/verification/records/{vid}/qr`.
- Public Ed25519 verify key endpoint: `/api/v1/verification/public-key`.
- Credential revocation endpoint with RBAC and institutional IDOR checks:
  `POST /api/v1/verification/records/{vid}/revoke`.
- Student verification details for college & AICTE portal:
  `GET /api/v1/verification/students/{student_id}`.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user, require_roles
from app.auth.rate_limiter import RateLimiter
from app.config import get_settings
from app.db import get_db
from app.models import Student, User, VerifiedRecord
from app.verification.service import (
    generate_qr_code_png,
    revoke_verified_record,
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


@router.get(
    "/verify",
    dependencies=[Depends(verify_rate_limiter)],
)
def verify_record_query(
    vid: str | None = Query(None, description="Verification ID from credential QR code"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Public verification lookup endpoint.

    Rate-limited to prevent enumeration attacks.
    SPEC.md Section 14:
    - Verifies Ed25519 signature over canonical payload.
    - Exposes minimal fields: institution, course, years, status, verification ID.
    - Never exposes personal data (DOB, category, contacts).
    """
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
    """Public record status and cryptographic proof lookup.

    Rate-limited to prevent brute-force ID scanning.
    """
    clean_vid = verification_id.strip()
    if len(clean_vid) < 5:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification record not found",
        )

    vr = db.scalar(
        select(VerifiedRecord).where(VerifiedRecord.verification_id == clean_vid)
    )
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
    """Generate high-contrast QR code PNG encoding link to `/verify?vid={vid}`.

    SPEC.md Section 14:
    - QR code encodes a link to `/verify?vid=...`, containing no personal data.
    """
    clean_vid = verification_id.strip()
    vr = db.scalar(
        select(VerifiedRecord.id).where(VerifiedRecord.verification_id == clean_vid)
    )
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
            "issued under the Smart India Hackathon APAAR platform."
        ),
    }


@router.post(
    "/records/{verification_id}/revoke",
    dependencies=[
        Depends(require_roles("aicte_admin", "aicte_officer", "college_admin"))
    ],
)
def revoke_record_endpoint(
    verification_id: str,
    payload: RevokeRecordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Revoke an active student verification record.

    Protected:
    - AICTE admin and officers can revoke any record.
    - College admin can only revoke credentials of students in their own institution.
    """
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
    """Get verified credential details for a student.

    Institutions can only view credentials of students enrolled at their own institution.
    """
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

    # Scoping check for college users
    if current_user.role in ("college_admin", "college_staff", "college_viewer"):
        if student.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view verification details for this student.",
            )

    vr = db.scalar(
        select(VerifiedRecord).where(VerifiedRecord.student_id == student_id)
    )

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
