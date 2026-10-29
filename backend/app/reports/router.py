"""FastAPI router for regulatory reports and data exports."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_aicte_user,
    require_college_user,
)
from app.auth.schemas import Role
from app.db import get_db
from app.models import User
from app.reports import service
from app.reports.schemas import (
    ReportFormat,
    ReportPreviewResponse,
    ReportType,
)

router = APIRouter(prefix="/reports", tags=["Reports & Data Exports"])
institution_reports_router = APIRouter(
    prefix="/institutions/{institution_id}/reports",
    tags=["Institution Reports"],
)


# Helper: File Download Response


def make_download_response(content: bytes, media_type: str, filename: str) -> Response:
    """Construct an HTTP Response with Content-Disposition attachment."""
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


# National AICTE Reports (AICTE Only)


@router.get(
    "/enrolment-by-state-course",
    summary="Download Enrolment by State and Course Report (AICTE only)",
)
def download_enrolment_by_state_course(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    format: Annotated[ReportFormat, Query(description="Export format")] = ReportFormat.CSV,
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
    state: Annotated[str | None, Query(description="Filter by state")] = None,
    course: Annotated[str | None, Query(description="Filter by course name")] = None,
) -> Response:
    """Download national enrolment, sanctioned intake, and fill rate report."""
    content, media_type, filename = service.generate_report(
        db=db,
        report_type=ReportType.ENROLMENT_BY_STATE_COURSE,
        output_format=format,
        current_user=current_user,
        academic_year=academic_year,
        state=state,
        course=course,
    )
    return make_download_response(content, media_type, filename)


@router.get(
    "/seat-utilisation",
    summary="Download Seat Utilisation and Intake Compliance Report (AICTE only)",
)
def download_seat_utilisation(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    format: Annotated[ReportFormat, Query(description="Export format")] = ReportFormat.CSV,
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
    state: Annotated[str | None, Query(description="Filter by state")] = None,
    course: Annotated[str | None, Query(description="Filter by course name")] = None,
) -> Response:
    """Download seat utilisation, approved intake quotas, and over-intake tracking."""
    content, media_type, filename = service.generate_report(
        db=db,
        report_type=ReportType.SEAT_UTILISATION,
        output_format=format,
        current_user=current_user,
        academic_year=academic_year,
        state=state,
        course=course,
    )
    return make_download_response(content, media_type, filename)


@router.get(
    "/colleges-with-exceptions",
    summary="Download Colleges with Exceptions Report (AICTE only)",
)
def download_colleges_with_exceptions(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    format: Annotated[ReportFormat, Query(description="Export format")] = ReportFormat.CSV,
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
    state: Annotated[str | None, Query(description="Filter by state")] = None,
    course: Annotated[str | None, Query(description="Filter by course name")] = None,
) -> Response:
    """Download exceptions register with written justifications and evidence links."""
    content, media_type, filename = service.generate_report(
        db=db,
        report_type=ReportType.COLLEGES_WITH_EXCEPTIONS,
        output_format=format,
        current_user=current_user,
        academic_year=academic_year,
        state=state,
        course=course,
    )
    return make_download_response(content, media_type, filename)


@router.get(
    "/duplicate-enrolments",
    summary="Download Cross-College Duplicate Enrolments Report (AICTE only)",
)
def download_duplicate_enrolments(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    format: Annotated[ReportFormat, Query(description="Export format")] = ReportFormat.CSV,
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
    state: Annotated[str | None, Query(description="Filter by state")] = None,
) -> Response:
    """Download cross-college multi-enrolment report with masked student IDs."""
    content, media_type, filename = service.generate_report(
        db=db,
        report_type=ReportType.DUPLICATE_ENROLMENTS,
        output_format=format,
        current_user=current_user,
        academic_year=academic_year,
        state=state,
    )
    return make_download_response(content, media_type, filename)


@router.get(
    "/year-over-year-trends",
    summary="Download Year-over-Year Admission Trends Report (AICTE only)",
)
def download_year_over_year_trends(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    format: Annotated[ReportFormat, Query(description="Export format")] = ReportFormat.CSV,
    base_year: Annotated[str, Query(description="Baseline year")] = "2025-26",
    target_year: Annotated[str, Query(description="Current target year")] = "2026-27",
    state: Annotated[str | None, Query(description="Filter by state")] = None,
    course: Annotated[str | None, Query(description="Filter by course name")] = None,
) -> Response:
    """Download comparative admissions, intake, and growth rate between academic years."""
    content, media_type, filename = service.generate_report(
        db=db,
        report_type=ReportType.YEAR_OVER_YEAR_TRENDS,
        output_format=format,
        current_user=current_user,
        base_year=base_year,
        target_year=target_year,
        state=state,
        course=course,
    )
    return make_download_response(content, media_type, filename)


# College & Institutional Reports (AICTE or Scoped College User)


@router.get(
    "/accreditation-snapshot",
    summary="Download College Accreditation Compliance Snapshot",
)
def download_accreditation_snapshot(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    format: Annotated[ReportFormat, Query(description="Export format")] = ReportFormat.PDF,
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
    institution_id: Annotated[int | None, Query(description="Institution ID")] = None,
) -> Response:
    """Download comprehensive accreditation compliance report for an institution."""
    content, media_type, filename = service.generate_report(
        db=db,
        report_type=ReportType.ACCREDITATION_SNAPSHOT,
        output_format=format,
        current_user=current_user,
        academic_year=academic_year,
        institution_id=institution_id,
    )
    return make_download_response(content, media_type, filename)


@router.get(
    "/college-submission",
    summary="Download College Official Submission Report",
)
def download_college_submission(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    format: Annotated[ReportFormat, Query(description="Export format")] = ReportFormat.PDF,
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
    institution_id: Annotated[int | None, Query(description="Institution ID")] = None,
    course_id: Annotated[int | None, Query(description="Filter by course ID")] = None,
) -> Response:
    """Download official student submission register and receipt for an institution."""
    content, media_type, filename = service.generate_report(
        db=db,
        report_type=ReportType.COLLEGE_SUBMISSION,
        output_format=format,
        current_user=current_user,
        academic_year=academic_year,
        institution_id=institution_id,
        course_id=course_id,
    )
    return make_download_response(content, media_type, filename)


# Preview Endpoint (JSON) for Frontend Interactive Tables


@router.get(
    "/preview",
    response_model=ReportPreviewResponse,
    summary="Preview report tabular data before downloading",
)
def preview_report(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    report_type: Annotated[ReportType, Query(description="Report type to preview")],
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
    state: Annotated[str | None, Query(description="State filter")] = None,
    course: Annotated[str | None, Query(description="Course filter")] = None,
    institution_id: Annotated[int | None, Query(description="Institution ID")] = None,
    course_id: Annotated[int | None, Query(description="Course ID")] = None,
    base_year: Annotated[str, Query(description="Base year for YoY")] = "2025-26",
    target_year: Annotated[str, Query(description="Target year for YoY")] = "2026-27",
) -> ReportPreviewResponse:
    """Retrieve structured JSON of columns, rows, summary metrics, and totals."""
    # Check permissions for national vs institutional reports
    if report_type in [
        ReportType.ENROLMENT_BY_STATE_COURSE,
        ReportType.SEAT_UTILISATION,
        ReportType.COLLEGES_WITH_EXCEPTIONS,
        ReportType.DUPLICATE_ENROLMENTS,
        ReportType.YEAR_OVER_YEAR_TRENDS,
    ]:
        if current_user.role not in Role.aicte_roles():
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: AICTE administrative role required for national reports",
            )

    if report_type == ReportType.ENROLMENT_BY_STATE_COURSE:
        data = service.generate_enrolment_by_state_course(
            db, academic_year=academic_year, state=state, course=course
        )
    elif report_type == ReportType.SEAT_UTILISATION:
        data = service.generate_seat_utilisation(
            db, academic_year=academic_year, state=state, course=course
        )
    elif report_type == ReportType.COLLEGES_WITH_EXCEPTIONS:
        data = service.generate_colleges_with_exceptions(
            db, academic_year=academic_year, state=state, course=course
        )
    elif report_type == ReportType.DUPLICATE_ENROLMENTS:
        data = service.generate_duplicate_enrolments(db, academic_year=academic_year, state=state)
    elif report_type == ReportType.YEAR_OVER_YEAR_TRENDS:
        data = service.generate_year_over_year_trends(
            db,
            state=state,
            course=course,
            base_year=base_year,
            target_year=target_year,
        )
    elif report_type == ReportType.ACCREDITATION_SNAPSHOT:
        target_id = institution_id or current_user.institution_id
        service.check_institution_access(target_id, current_user)
        data = service.generate_accreditation_snapshot(
            db, institution_id=target_id, academic_year=academic_year
        )
    elif report_type == ReportType.COLLEGE_SUBMISSION:
        target_id = institution_id or current_user.institution_id
        service.check_institution_access(target_id, current_user)
        data = service.generate_college_submission_report(
            db,
            institution_id=target_id,
            academic_year=academic_year,
            course_id=course_id,
        )

    return ReportPreviewResponse(
        report_type=data.report_type.value,
        title=data.title,
        subtitle=data.subtitle,
        academic_year=data.academic_year,
        generated_at=data.generated_at,
        filters_applied=data.filters_applied,
        summary_boxes=data.summary_boxes,
        columns=data.columns,
        rows=data.rows,
        totals_row=data.totals_row,
        total_records=len(data.rows),
        notes=data.notes,
    )


# Institution-Scoped Convenience Routes (For College UI)


@institution_reports_router.get(
    "/submission",
    summary="Download College Submission Report by Institution Route",
)
def download_institution_submission(
    institution_id: int,
    current_user: Annotated[User, require_college_user],
    db: Annotated[Session, Depends(get_db)],
    format: Annotated[ReportFormat, Query(description="Export format")] = ReportFormat.PDF,
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
    course_id: Annotated[int | None, Query(description="Filter by course ID")] = None,
) -> Response:
    """College-scoped endpoint to download its own submission report."""
    content, media_type, filename = service.generate_report(
        db=db,
        report_type=ReportType.COLLEGE_SUBMISSION,
        output_format=format,
        current_user=current_user,
        academic_year=academic_year,
        institution_id=institution_id,
        course_id=course_id,
    )
    return make_download_response(content, media_type, filename)


@institution_reports_router.get(
    "/accreditation",
    summary="Download College Accreditation Snapshot by Institution Route",
)
def download_institution_accreditation(
    institution_id: int,
    current_user: Annotated[User, require_college_user],
    db: Annotated[Session, Depends(get_db)],
    format: Annotated[ReportFormat, Query(description="Export format")] = ReportFormat.PDF,
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
) -> Response:
    """College-scoped endpoint to download its own accreditation snapshot."""
    content, media_type, filename = service.generate_report(
        db=db,
        report_type=ReportType.ACCREDITATION_SNAPSHOT,
        output_format=format,
        current_user=current_user,
        academic_year=academic_year,
        institution_id=institution_id,
    )
    return make_download_response(content, media_type, filename)
