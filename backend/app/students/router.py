"""API routes for student records, uploads, and seat declarations."""

import io
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    get_db,
    require_college_staff,
    verify_institution_access,
)
from app.models import Student, User
from app.students import seat_declarations as seat_service
from app.students import service as student_service
from app.students import upload_service
from app.students.schemas import (
    CourseSummaryResponse,
    InstitutionSeatDeclarationResponse,
    SeatDeclarationBatchSaveRequest,
    SeatDeclarationSaveRequest,
    StudentCreateRequest,
    StudentListResponse,
    StudentResponse,
    StudentSaveResultResponse,
    StudentUpdateRequest,
    UploadHistoryResponse,
    UploadResultResponse,
)

router = APIRouter(tags=["Seat Declarations & Student Management"])

college_staff_guard = require_college_staff


# Seat Declarations & Course Summary Endpoints (Spec 8.1, 13, TASKS.md T19)


@router.get(
    "/institutions/{institution_id}/seat-declarations",
    response_model=InstitutionSeatDeclarationResponse,
    summary="Get all course summaries and seat declarations for an institution",
)
def get_institution_seat_declarations(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    db: Annotated[Session, Depends(get_db)],
    academic_year: str = Query(default="2026-27", description="Academic year"),
) -> InstitutionSeatDeclarationResponse:
    """Retrieve course summary table and seat declarations for an institution.

    Spec 8.1 & 13:
    - Lists approved courses with read-only approved intake and supernumerary allowed.
    - Shows calculated active student enrolments from student records.
    - Returns declared seat counts and live validation status badges.
    """
    return seat_service.get_institution_seat_declarations(
        db=db,
        institution_id=institution_id,
        academic_year=academic_year,
    )


@router.get(
    "/institutions/{institution_id}/courses/{course_id}/seat-declaration",
    response_model=CourseSummaryResponse,
    summary="Get course summary and seat declaration for a single course",
)
def get_course_seat_declaration(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    course_id: int,
    db: Annotated[Session, Depends(get_db)],
    academic_year: str = Query(default="2026-27", description="Academic year"),
) -> CourseSummaryResponse:
    """Retrieve seat declaration and live validation status for a single course."""
    return seat_service.get_course_summary(
        db=db,
        institution_id=institution_id,
        course_id=course_id,
        academic_year=academic_year,
    )


@router.put(
    "/institutions/{institution_id}/courses/{course_id}/seat-declaration",
    response_model=CourseSummaryResponse,
    summary="Save or autosave a course seat declaration as draft (College Staff only)",
)
def save_course_seat_declaration(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    course_id: int,
    payload: SeatDeclarationSaveRequest,
    request: Request,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> CourseSummaryResponse:
    """Save or autosave a course seat declaration.

    Spec 8.1 & 13, TASKS.md T19:
    - Autosaves as a draft; invalid values show errors immediately but are still saved.
    - Enforces IDOR protection and institution approval status checks.
    - Emits audit log entry for changes.
    """
    client_ip = request.client.host if request.client else None
    return seat_service.save_course_seat_declaration(
        db=db,
        institution_id=institution_id,
        course_id=course_id,
        payload=payload,
        user=current_user,
        client_ip=client_ip,
    )


@router.put(
    "/institutions/{institution_id}/seat-declarations",
    response_model=InstitutionSeatDeclarationResponse,
    summary="Batch save or autosave seat declarations for multiple courses (College Staff only)",
)
def batch_save_seat_declarations(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    payload: SeatDeclarationBatchSaveRequest,
    request: Request,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> InstitutionSeatDeclarationResponse:
    """Batch save or autosave declarations across multiple approved courses."""
    client_ip = request.client.host if request.client else None
    return seat_service.batch_save_seat_declarations(
        db=db,
        institution_id=institution_id,
        payload=payload,
        user=current_user,
        client_ip=client_ip,
    )


# Single Student Entry & Directory Endpoints (Spec 8.2, 9.4, TASKS.md T20)


@router.get(
    "/institutions/{institution_id}/students",
    response_model=StudentListResponse,
    summary="List student records with status, flag level, and search filters",
)
def list_students(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    db: Annotated[Session, Depends(get_db)],
    academic_year: str | None = Query(default="2026-27", description="Filter by academic year"),
    course_id: int | None = Query(default=None, description="Filter by course ID"),
    status: str | None = Query(
        default=None, description="Filter by status (draft, valid, flagged, etc.)"
    ),
    level: str | None = Query(
        default=None, description="Filter by flag level (error, exception, warning, info, clean)"
    ),
    search: str | None = Query(
        default=None, description="Search by name, APAAR ID, or enrolment number"
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> StudentListResponse:
    """Retrieve filtered and paginated list of student records for an institution."""
    return student_service.list_students(
        db=db,
        institution_id=institution_id,
        academic_year=academic_year,
        course_id=course_id,
        status_filter=status,
        level_filter=level,
        search=search,
        page=page,
        limit=limit,
    )


# Bulk Upload & Evaluation Endpoints (Spec 8.2, 9.4, 13, TASKS.md T21)


@router.get(
    "/institutions/{institution_id}/students/upload/template",
    summary="Download canonical student bulk upload CSV template",
)
def download_student_template(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[User, college_staff_guard],
) -> Response:
    """Return canonical CSV template containing required lowercase headers.

    Spec 8.2 & TASKS.md T21:
    - Headers: apaar_id, name, dob, gender, course, branch, admission_year, enrolment_no,
      admission_date, admission_mode, seat_type, reservation_category, nri, oci,
      foreign_national, country.
    """
    csv_content = upload_service.generate_template_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="apaar_student_upload_template.csv"'},
    )


@router.post(
    "/institutions/{institution_id}/students/upload",
    response_model=UploadResultResponse,
    status_code=201,
    summary="Upload bulk student file (CSV/Excel) and execute validation engine",
)
async def upload_students_file(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    request: Request,
    file: UploadFile = File(...),
    academic_year: str = Form(default="2026-27"),
    current_user: Annotated[User, college_staff_guard] = None,  # type: ignore[assignment]
    db: Session = Depends(get_db),  # type: ignore[assignment]
) -> UploadResultResponse:
    """Upload CSV or Excel file of student records.

    Spec 8.2, 9.4, 13 & TASKS.md T21:
    - Rejection policy: reject only unreadable, empty, or oversized files.
    - Saves all rows as drafts without silently discarding data.
    - Re-upload updates matching records (same college, course, year, APAAR ID).
    - Runs pure validation engine across all rows and persists flags.
    - Emits hash-chained audit log entry.
    """
    client_ip = request.client.host if request.client else None
    file_bytes = await file.read()
    filename = file.filename or "uploaded_students.csv"

    return upload_service.process_bulk_upload(
        db=db,
        institution_id=institution_id,
        file_bytes=file_bytes,
        filename=filename,
        user=current_user,
        academic_year_default=academic_year,
        client_ip=client_ip,
    )


@router.get(
    "/institutions/{institution_id}/students/uploads",
    response_model=UploadHistoryResponse,
    summary="Retrieve bulk student upload history for an institution",
)
def get_upload_history(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> UploadHistoryResponse:
    """Retrieve historical bulk uploads with row counts, status, and summary metadata."""
    return upload_service.get_upload_history(
        db=db,
        institution_id=institution_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/institutions/{institution_id}/students/uploads/{upload_id}",
    response_model=UploadResultResponse,
    summary="Retrieve evaluation details and row flags for a past upload",
)
def get_upload_details(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    upload_id: int,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> UploadResultResponse:
    """Retrieve full evaluation details, stats, and row-level flags for an upload."""
    return upload_service.get_upload_details(
        db=db,
        institution_id=institution_id,
        upload_id=upload_id,
    )


@router.get(
    "/institutions/{institution_id}/students/uploads/{upload_id}/errors",
    summary="Download error CSV file with fix hints for an upload",
)
def download_upload_errors(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    upload_id: int,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Export error CSV containing (row, field, code, level, message, fix hint)."""
    csv_content = upload_service.generate_error_csv(
        db=db,
        institution_id=institution_id,
        upload_id=upload_id,
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="upload_{upload_id}_errors.csv"'},
    )


@router.get(
    "/institutions/{institution_id}/students/{student_id}",
    response_model=StudentResponse,
    summary="Get details of a single student record",
)
def get_student(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    student_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> StudentResponse:
    """Retrieve full details of a student record including decrypted data and active flags."""
    return student_service.get_student(
        db=db,
        institution_id=institution_id,
        student_id=student_id,
    )


@router.get(
    "/institutions/{institution_id}/students/{student_id}/certificate",
    summary="Download degree certificate PDF with side-by-side College ID and APAAR ID",
)
def get_student_certificate_endpoint(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    student_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    download: bool = Query(False, description="Whether to trigger file download attachment"),
) -> StreamingResponse:
    """Generate and return official degree certificate PDF for a student.

    Spec: Section 17 & TASKS.md T35:
    - Sample degree certificate with college student ID and APAAR ID side by side and the QR code.
    - Endpoint for institutions; scanning the QR leads to the verify flow.
    """
    from app.verification.service import generate_student_certificate_service

    student = db.scalar(
        select(Student).where(
            Student.id == student_id,
            Student.institution_id == institution_id,
        )
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student #{student_id} not found under institution #{institution_id}.",
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


@router.post(
    "/institutions/{institution_id}/students",
    response_model=StudentSaveResultResponse,
    status_code=201,
    summary="Create student draft record and execute validation ('Check and save')",
)
def create_student(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    payload: StudentCreateRequest,
    request: Request,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> StudentSaveResultResponse:
    """Create a single student record as draft and run validation engine immediately.

    Spec 8.2 & 9.4:
    - Never discard data: saved as draft either way.
    - Runs cheap checks, APAAR lookups, and duplicate checks immediately.
    - Persists validation flags with row reference.
    - Country field persisted only when foreign_national is Yes.
    """
    client_ip = request.client.host if request.client else None
    return student_service.create_student(
        db=db,
        institution_id=institution_id,
        payload=payload,
        user=current_user,
        client_ip=client_ip,
    )


@router.put(
    "/institutions/{institution_id}/students/{student_id}",
    response_model=StudentSaveResultResponse,
    summary="Update an existing student draft record and re-validate ('Check and save')",
)
def update_student(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    student_id: int,
    payload: StudentUpdateRequest,
    request: Request,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> StudentSaveResultResponse:
    """Update student draft fields and re-run validation engine.

    Spec 8.2, 9.4, 10:
    - Locked records cannot be edited directly (403 Forbidden).
    - Preserves existing justifications on still-applicable flags.
    - Emits hash-chained audit log entry.
    """
    client_ip = request.client.host if request.client else None
    return student_service.update_student(
        db=db,
        institution_id=institution_id,
        student_id=student_id,
        payload=payload,
        user=current_user,
        client_ip=client_ip,
    )


@router.delete(
    "/institutions/{institution_id}/students/{student_id}",
    summary="Delete a student draft record",
)
def delete_student(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    student_id: int,
    request: Request,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Delete a student draft record.

    Spec 8.2, 10:
    - Locked records cannot be deleted (403 Forbidden).
    - Resolves cross-college duplicate flags if applicable.
    - Emits hash-chained audit log entry.
    """
    client_ip = request.client.host if request.client else None
    return student_service.delete_student(
        db=db,
        institution_id=institution_id,
        student_id=student_id,
        user=current_user,
        client_ip=client_ip,
    )
