"""Service logic for validation flags, justifications, storage integration, and gate checks."""

import mimetypes
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.audit import service as audit_service
from app.integrations.factory import get_storage
from app.models import Course, Justification, Student, Submission, User, ValidationFlag
from app.submissions.schemas import (
    FlagTargetCourse,
    FlagTargetStudent,
    InstitutionFlagsListResponse,
    JustificationResponse,
    ValidationFlagDetailResponse,
    ValidationFlagsSummary,
)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".doc", ".csv"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _sanitize_filename(filename: str) -> str:
    """Sanitize user-provided filename to prevent directory traversal or invalid characters."""
    clean = Path(filename).name
    clean = re.sub(r"[^\w\-.]", "_", clean)
    return clean[:80] or "attachment"


def get_flag_or_404(
    db: Session,
    flag_id: int,
    institution_id: int,
) -> ValidationFlag:
    """Retrieve validation flag and verify it belongs to the given institution."""
    stmt = (
        select(ValidationFlag)
        .outerjoin(Student, ValidationFlag.student_id == Student.id)
        .outerjoin(Course, ValidationFlag.course_id == Course.id)
        .outerjoin(Submission, ValidationFlag.submission_id == Submission.id)
        .options(
            selectinload(ValidationFlag.justifications).joinedload(Justification.author),
            joinedload(ValidationFlag.student).joinedload(Student.course),
            joinedload(ValidationFlag.course),
            joinedload(ValidationFlag.submission),
        )
        .where(
            ValidationFlag.id == flag_id,
            or_(
                Student.institution_id == institution_id,
                Course.institution_id == institution_id,
                Submission.institution_id == institution_id,
            ),
        )
    )
    flag = db.scalar(stmt)
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation flag #{flag_id} not found for institution #{institution_id}",
        )
    return flag


def map_justification_to_response(
    justification: Justification,
    institution_id: int,
) -> JustificationResponse:
    """Convert Justification ORM entity into typed response schema with document URL."""
    doc_url: str | None = None
    if justification.document_ref:
        doc_url = (
            f"/api/v1/institutions/{institution_id}/justifications/"
            f"{justification.id}/document"
        )

    author_name: str | None = None
    author_role: str | None = None
    if justification.author:
        author_name = justification.author.email
        author_role = justification.author.role

    return JustificationResponse(
        id=justification.id,
        flag_id=justification.flag_id,
        text=justification.text,
        document_ref=justification.document_ref,
        document_url=doc_url,
        by_user=justification.by_user,
        author_name=author_name,
        author_role=author_role,
        at=justification.at,
        created_at=justification.created_at,
        updated_at=justification.updated_at,
    )


def map_flag_to_response(
    flag: ValidationFlag,
    institution_id: int,
) -> ValidationFlagDetailResponse:
    """Convert ValidationFlag ORM entity into typed response schema with target metadata."""
    student_target: FlagTargetStudent | None = None
    if flag.student:
        course_name = flag.student.course.name if flag.student.course else None
        branch_name = flag.student.course.branch if flag.student.course else None
        student_target = FlagTargetStudent(
            id=flag.student.id,
            apaar_id=flag.student.apaar_id,
            name=flag.student.name,
            enrolment_no=flag.student.enrolment_no,
            academic_year=flag.student.academic_year,
            course_name=course_name,
            branch=branch_name,
        )

    course_target: FlagTargetCourse | None = None
    if flag.course:
        course_target = FlagTargetCourse(
            id=flag.course.id,
            name=flag.course.name,
            branch=flag.course.branch,
            level=flag.course.level,
        )

    justifications = [
        map_justification_to_response(j, institution_id)
        for j in (flag.justifications or [])
    ]

    return ValidationFlagDetailResponse(
        id=flag.id,
        student_id=flag.student_id,
        course_id=flag.course_id,
        submission_id=flag.submission_id,
        rule_code=flag.rule_code,
        level=flag.level,
        field=flag.field,
        message=flag.message,
        fix_hint=flag.fix_hint,
        audience=flag.audience,
        requires_justification=flag.requires_justification,
        status=flag.status,
        student=student_target,
        course=course_target,
        justifications=justifications,
        created_at=flag.created_at,
        updated_at=flag.updated_at,
    )


def list_institution_flags(
    db: Session,
    institution_id: int,
    academic_year: str | None = None,
    level: str | None = None,
    flag_status: str | None = None,
    rule_code: str | None = None,
    course_id: int | None = None,
    student_id: int | None = None,
    requires_justification: bool | None = None,
    search: str | None = None,
) -> InstitutionFlagsListResponse:
    """Query validation flags belonging to an institution with rich filtering and stats summary."""
    base_ownership_filter = or_(
        Student.institution_id == institution_id,
        Course.institution_id == institution_id,
        Submission.institution_id == institution_id,
    )

    stmt = (
        select(ValidationFlag)
        .outerjoin(Student, ValidationFlag.student_id == Student.id)
        .outerjoin(Course, ValidationFlag.course_id == Course.id)
        .outerjoin(Submission, ValidationFlag.submission_id == Submission.id)
        .options(
            selectinload(ValidationFlag.justifications).joinedload(Justification.author),
            joinedload(ValidationFlag.student).joinedload(Student.course),
            joinedload(ValidationFlag.course),
            joinedload(ValidationFlag.submission),
        )
        .where(base_ownership_filter)
    )

    if academic_year:
        stmt = stmt.where(
            or_(
                Student.academic_year == academic_year,
                Submission.academic_year == academic_year,
            )
        )

    if level:
        stmt = stmt.where(ValidationFlag.level == level.lower())

    if flag_status:
        stmt = stmt.where(ValidationFlag.status == flag_status.lower())

    if rule_code:
        stmt = stmt.where(ValidationFlag.rule_code == rule_code.upper())

    if course_id:
        stmt = stmt.where(
            or_(
                ValidationFlag.course_id == course_id,
                Student.course_id == course_id,
            )
        )

    if student_id:
        stmt = stmt.where(ValidationFlag.student_id == student_id)

    if requires_justification is not None:
        stmt = stmt.where(ValidationFlag.requires_justification == requires_justification)

    if search:
        s = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                ValidationFlag.rule_code.ilike(s),
                ValidationFlag.message.ilike(s),
                ValidationFlag.field.ilike(s),
                Student.name.ilike(s),
                Student.apaar_id.ilike(s),
                Student.enrolment_no.ilike(s),
            )
        )

    # Order by severity level then status then id
    stmt = stmt.order_by(
        ValidationFlag.level.asc(),
        ValidationFlag.status.asc(),
        ValidationFlag.id.desc(),
    )

    flags = db.scalars(stmt).unique().all()

    # Calculate summary over institutional flags (respecting academic_year filter if specified)
    summary_stmt = (
        select(
            ValidationFlag.level,
            ValidationFlag.status,
            ValidationFlag.requires_justification,
            func.count(ValidationFlag.id),
        )
        .outerjoin(Student, ValidationFlag.student_id == Student.id)
        .outerjoin(Course, ValidationFlag.course_id == Course.id)
        .outerjoin(Submission, ValidationFlag.submission_id == Submission.id)
        .where(base_ownership_filter)
    )
    if academic_year:
        summary_stmt = summary_stmt.where(
            or_(
                Student.academic_year == academic_year,
                Submission.academic_year == academic_year,
            )
        )
    summary_stmt = summary_stmt.group_by(
        ValidationFlag.level,
        ValidationFlag.status,
        ValidationFlag.requires_justification,
    )
    summary_rows = db.execute(summary_stmt).all()

    summary = ValidationFlagsSummary()
    for row_level, row_status, req_just, count in summary_rows:
        summary.total_flags += count

        if row_status == "open":
            summary.open_count += count
        elif row_status == "justified":
            summary.justified_count += count
        elif row_status == "resolved":
            summary.resolved_count += count

        if row_level == "error":
            summary.error_count += count
        elif row_level == "exception":
            summary.exception_count += count
        elif row_level == "warning":
            summary.warning_count += count
        elif row_level == "info":
            summary.info_count += count

        # A flag blocks final submit if it is OPEN and:
        # - It is an error (data is invalid, must be fixed), OR
        # - It is an exception (compliance violation, requires justification), OR
        # - It is a warning that explicitly requires justification
        if row_status == "open":
            if row_level == "error":
                summary.blocking_count += count
            elif row_level == "exception":
                summary.blocking_count += count
            elif row_level == "warning" and req_just:
                summary.blocking_count += count

    summary.can_submit = summary.blocking_count == 0

    items = [map_flag_to_response(fl, institution_id) for fl in flags]
    return InstitutionFlagsListResponse(
        institution_id=institution_id,
        academic_year=academic_year,
        summary=summary,
        items=items,
    )


async def create_flag_justification(
    db: Session,
    institution_id: int,
    flag_id: int,
    user: User,
    text: str,
    document_file: UploadFile | None = None,
    document_ref: str | None = None,
) -> JustificationResponse:
    """Submit written justification and document for an exception or warning flag.

    Rules enforced:
    - College admin or college staff only (SPEC.md Section 5).
    - Error-level flags cannot be justified; underlying data must be fixed (SPEC.md Section 9.1).
    - Exception and warning flags transition to status 'justified' (SPEC.md Section 9.1 & 10).
    - Supporting documents are stored via the Storage interface (Hard Rule 5).
    - State transition is recorded in the hash-chained audit log (Hard Rule 6).
    """
    flag = get_flag_or_404(db=db, flag_id=flag_id, institution_id=institution_id)

    # 1. Enforce SPEC.md Section 9.1: error flags cannot be justified
    if flag.level == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Error-level flags ({flag.rule_code}) cannot be justified. "
                "The underlying student or institutional data contains errors "
                "and must be corrected."
            ),
        )

    # 2. Validate justification text
    clean_text = text.strip() if text else ""
    if len(clean_text) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Justification explanation must be at least 5 characters long.",
        )

    # 3. Handle document upload via Storage interface
    final_doc_ref = document_ref
    if document_file is not None and document_file.filename:
        filename = document_file.filename
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            allowed_str = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported document format '{ext}'. Allowed: {allowed_str}",
            )

        raw_bytes = await document_file.read()
        if len(raw_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB.",
            )

        clean_fn = _sanitize_filename(filename)
        storage_path = (
            f"justifications/{institution_id}/flag_{flag.id}_{uuid.uuid4().hex[:8]}_{clean_fn}"
        )
        ct = (
            document_file.content_type
            or mimetypes.guess_type(clean_fn)[0]
            or "application/octet-stream"
        )

        storage = get_storage()
        final_doc_ref = storage.save(storage_path, raw_bytes, ct)

    # 4. Create justification record
    justification = Justification(
        flag_id=flag.id,
        text=clean_text,
        document_ref=final_doc_ref,
        by_user=user.id,
        at=datetime.now(UTC),
    )
    db.add(justification)

    # 5. Transition flag status to 'justified'
    prev_status = flag.status
    flag.status = "justified"
    db.flush()

    # 6. Audit log entry (Hard Rule 6)
    audit_service.record(
        db=db,
        actor_id=user.id,
        actor_role=user.role,
        action="justification.create",
        entity="justification",
        entity_id=justification.id,
        before_json={"flag_id": flag.id, "status": prev_status},
        after_json={
            "flag_id": flag.id,
            "status": "justified",
            "rule_code": flag.rule_code,
            "level": flag.level,
            "text": clean_text,
            "document_ref": final_doc_ref,
        },
    )

    db.commit()
    db.refresh(justification)
    return map_justification_to_response(justification, institution_id)


def get_justification_document_file(
    db: Session,
    institution_id: int,
    justification_id: int,
    user: User,
) -> tuple[bytes, str, str]:
    """Retrieve attached justification document content from Storage interface.

    Returns:
        (content_bytes, filename, media_type)
    """
    stmt = (
        select(Justification)
        .options(joinedload(Justification.flag))
        .where(Justification.id == justification_id)
    )
    justification = db.scalar(stmt)
    if not justification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Justification #{justification_id} not found",
        )

    # Verify institution ownership unless AICTE supervisory role
    if user.role not in {"aicte_admin", "aicte_officer"}:
        flag = get_flag_or_404(db=db, flag_id=justification.flag_id, institution_id=institution_id)
        if flag.id != justification.flag_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot access document from another institution",
            )

    if not justification.document_ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document attached to this justification.",
        )

    storage = get_storage()
    try:
        content = storage.get(justification.document_ref)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Justification file was not found in storage.",
        ) from None

    filename = Path(justification.document_ref).name
    media_type, _ = mimetypes.guess_type(filename)
    if not media_type:
        media_type = "application/pdf" if filename.endswith(".pdf") else "application/octet-stream"

    return content, filename, media_type


def delete_flag_justification(
    db: Session,
    institution_id: int,
    justification_id: int,
    user: User,
) -> dict[str, Any]:
    """Remove a justification before final submission. Reverts flag to open if none remain."""
    stmt = (
        select(Justification)
        .options(joinedload(Justification.flag))
        .where(Justification.id == justification_id)
    )
    justification = db.scalar(stmt)
    if not justification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Justification #{justification_id} not found",
        )

    flag = get_flag_or_404(db=db, flag_id=justification.flag_id, institution_id=institution_id)

    # Clean up storage if document ref exists
    if justification.document_ref:
        storage = get_storage()
        try:
            storage.delete(justification.document_ref)
        except Exception:
            pass

    db.delete(justification)
    db.flush()

    # Check if remaining justifications exist for this flag
    remaining_count = db.scalar(
        select(func.count(Justification.id)).where(Justification.flag_id == flag.id)
    )
    if remaining_count == 0:
        flag.status = "open"

    audit_service.record(
        db=db,
        actor_id=user.id,
        actor_role=user.role,
        action="justification.delete",
        entity="justification",
        entity_id=justification_id,
        before_json={"flag_id": flag.id, "status": "justified"},
        after_json={"flag_id": flag.id, "status": flag.status},
    )

    db.commit()
    return {"message": "Justification deleted", "flag_id": flag.id, "flag_status": flag.status}
