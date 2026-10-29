"""External Integration API for Student Data Synchronization (ERP / SIS Integration)."""

from __future__ import annotations

from typing import Annotated, Any

import redis
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_api_key_scope,
    verify_api_key,
)
from app.db import get_db, get_redis
from app.models import ApiKey, Institution
from app.students import upload_service
from app.students.schemas import UploadResultResponse

router = APIRouter(prefix="/integration", tags=["Integration API (ERP / SIS)"])


# Schemas & OpenAPI Examples


class IntegrationStudentItem(BaseModel):
    """Student data record for bulk JSON integration push."""

    apaar_id: str = Field(..., description="12-digit APAAR ID (e.g. 900012345678)")
    name: str = Field(..., description="Student full name as per official records")
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    gender: str = Field(default="Male", description="Gender (Male, Female, Other)")
    course: str = Field(..., description="Approved programme name (e.g. Computer Science)")
    branch: str | None = Field(default="", description="Branch or specialisation")
    course_id: int | None = Field(default=None, description="Optional internal course identifier")
    admission_year: str | None = Field(
        default=None, description="Academic year (e.g. 2026-27). Defaults to batch year"
    )
    enrolment_no: str = Field(
        ..., description="Institution student enrolment/roll number (unique per course)"
    )
    admission_date: str = Field(..., description="Date of admission in YYYY-MM-DD format")
    admission_mode: str = Field(
        default="State counselling",
        description="Mode of admission (e.g. State counselling, JEE Main, Management)",
    )
    seat_type: str = Field(
        default="Regular",
        description="Seat category (Regular, Supernumerary, Management, TFWS)",
    )
    reservation_category: str = Field(
        default="General",
        description="Reservation category (General, OBC, SC, ST, EWS)",
    )
    nri: str | bool = Field(default="No", description="NRI status (Yes/No or boolean)")
    oci: str | bool = Field(default="No", description="OCI status (Yes/No or boolean)")
    foreign_national: str | bool = Field(
        default="No", description="Foreign national status (Yes/No or boolean)"
    )
    country: str | None = Field(
        default=None, description="Country of citizenship (required if foreign_national is Yes)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "apaar_id": "900012345678",
                "name": "Rahul Sharma",
                "dob": "2004-05-15",
                "gender": "Male",
                "course": "Computer Science and Engineering",
                "branch": "Computer Science",
                "enrolment_no": "ENR-2026-CS-001",
                "admission_date": "2026-07-15",
                "admission_mode": "State counselling",
                "seat_type": "Regular",
                "reservation_category": "General",
                "nri": "No",
                "oci": "No",
                "foreign_national": "No",
                "country": None,
            }
        }
    )


class IntegrationBulkUploadRequest(BaseModel):
    """Payload to push a batch of student records from an external ERP or SIS."""

    academic_year: str = Field(
        default="2026-27", description="Academic admission cycle (e.g. 2026-27)"
    )
    students: list[IntegrationStudentItem] = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="List of student records to ingest and validate",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "academic_year": "2026-27",
                "students": [
                    {
                        "apaar_id": "900012345678",
                        "name": "Rahul Sharma",
                        "dob": "2004-05-15",
                        "gender": "Male",
                        "course": "Computer Science and Engineering",
                        "branch": "Computer Science",
                        "enrolment_no": "ENR-2026-CS-001",
                        "admission_date": "2026-07-15",
                        "admission_mode": "State counselling",
                        "seat_type": "Regular",
                        "reservation_category": "General",
                        "nri": "No",
                        "oci": "No",
                        "foreign_national": "No",
                    },
                    {
                        "apaar_id": "900012345679",
                        "name": "Priya Patel",
                        "dob": "2004-08-22",
                        "gender": "Female",
                        "course": "Computer Science and Engineering",
                        "branch": "Computer Science",
                        "enrolment_no": "ENR-2026-CS-002",
                        "admission_date": "2026-07-16",
                        "admission_mode": "State counselling",
                        "seat_type": "Regular",
                        "reservation_category": "OBC",
                        "nri": "No",
                        "oci": "No",
                        "foreign_national": "No",
                    },
                ],
            }
        }
    )


class IntegrationIdentityResponse(BaseModel):
    """Identity details of authenticated integration API key and institution."""

    institution_id: int
    aicte_id: str
    institution_name: str
    api_key_id: int
    api_key_name: str
    scopes: list[str]


# Endpoints


@router.get(
    "/me",
    response_model=IntegrationIdentityResponse,
    summary="Inspect integration API key identity and scopes",
)
def get_integration_identity(
    auth: Annotated[tuple[Institution, ApiKey], Depends(verify_api_key)],
) -> IntegrationIdentityResponse:
    """Verify integration API key authentication and return institution scope."""
    institution, api_key = auth
    return IntegrationIdentityResponse(
        institution_id=institution.id,
        aicte_id=institution.aicte_id,
        institution_name=institution.name,
        api_key_id=api_key.id,
        api_key_name=api_key.name,
        scopes=list(api_key.scopes) if isinstance(api_key.scopes, list) else [],
    )


@router.post(
    "/students/bulk",
    response_model=UploadResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Push student records in bulk via JSON (ERP Integration)",
)
def bulk_push_students(
    payload: IntegrationBulkUploadRequest,
    request: Request,
    auth: Annotated[tuple[Institution, ApiKey], Depends(require_api_key_scope("students:write"))],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Response:
    """Ingest, update, and evaluate student records via JSON API.

    Spec 8.2, 9.4, 17 & TASKS.md T36:
    - Scoped API key authentication (requires `students:write` scope).
    - Idempotency-Key header support: returns cached result on retry.
    - Runs the unified pure validation engine across all submitted records.
    - Re-push updates matching existing draft records (same college, course, year, APAAR ID).
    - Persists flags, updates upload history, and writes hash-chained audit log.
    """
    institution, api_key = auth
    client_ip = request.client.host if request.client else None

    # Check for alternate header if standard was omitted
    effective_idempotency_key = idempotency_key or request.headers.get("x-idempotency-key")
    if effective_idempotency_key:
        effective_idempotency_key = effective_idempotency_key.strip()
        redis_cache_key = f"idempotency:{institution.id}:{effective_idempotency_key}"
        try:
            cached_json = redis_client.get(redis_cache_key)
            if cached_json:
                return Response(
                    content=cached_json,
                    media_type="application/json",
                    status_code=status.HTTP_200_OK,
                    headers={
                        "X-Idempotent-Replayed": "true",
                        "Idempotency-Key": effective_idempotency_key,
                    },
                )
        except Exception:
            pass  # Fallback gracefully if Redis cache lookup encounters transient issue

    raw_records: list[dict[str, Any]] = [s.model_dump() for s in payload.students]

    result: UploadResultResponse = upload_service.process_json_bulk_upload(
        db=db,
        institution_id=institution.id,
        records=raw_records,
        academic_year_default=payload.academic_year,
        api_key_name=api_key.name,
        api_key_id=api_key.id,
        client_ip=client_ip,
    )

    response_json = result.model_dump_json()

    # Cache response in Redis for 24 hours (86400 seconds) if idempotency key was supplied
    if effective_idempotency_key:
        redis_cache_key = f"idempotency:{institution.id}:{effective_idempotency_key}"
        try:
            redis_client.set(redis_cache_key, response_json, ex=86400)
        except Exception:
            pass

    return Response(
        content=response_json,
        media_type="application/json",
        status_code=status.HTTP_201_CREATED,
        headers={
            "X-Idempotent-Replayed": "false",
            "Idempotency-Key": effective_idempotency_key or "",
        },
    )


@router.post(
    "/institutions/{institution_id}/students/bulk",
    response_model=UploadResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Institution-scoped push student records in bulk via JSON (ERP Integration)",
)
def bulk_push_students_for_institution(
    institution_id: int,
    payload: IntegrationBulkUploadRequest,
    request: Request,
    auth: Annotated[tuple[Institution, ApiKey], Depends(require_api_key_scope("students:write"))],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Response:
    """Institution-scoped alias verifying path institution_id matches API key institution."""
    institution, _ = auth
    if institution.id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"API key belongs to institution #{institution.id}, "
                f"cannot upload to institution #{institution_id}"
            ),
        )
    return bulk_push_students(
        payload=payload,
        request=request,
        auth=auth,
        db=db,
        redis_client=redis_client,
        idempotency_key=idempotency_key,
    )
