"""Service logic for validation flags, justifications, storage integration, and gate checks."""

import mimetypes
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import redis
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.audit import service as audit_service
from app.auth.otp import store_and_send_otp, verify_otp
from app.institutions.service import check_institution_can_upload
from app.integrations.factory import get_storage
from app.models import (
    Course,
    Institution,
    Justification,
    SeatDeclaration,
    Student,
    Submission,
    User,
    ValidationFlag,
)
from app.submissions.schemas import (
    BlockerDetail,
    FlagTargetCourse,
    FlagTargetStudent,
    InstitutionFlagsListResponse,
    JustificationResponse,
    SubmissionGateResponse,
    SubmissionOtpResponse,
    SubmissionReceiptResponse,
    SubmissionSubmitRequest,
    ValidationFlagDetailResponse,
    ValidationFlagsSummary,
)
from app.submissions.state_machine import SubmissionState, SubmissionStateMachine

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


def check_submission_gate(
    db: Session,
    institution_id: int,
    academic_year: str = "2026-27",
) -> SubmissionGateResponse:
    """Evaluate final submit gate criteria and assemble blockers with deep navigation links.

    SPEC.md Section 10 & TASKS.md T23:
    - Blocks if any error flag is open.
    - Blocks if seat declarations differ from enrolled student records.
    - Blocks if exceptions or justification-required warnings lack justifications.
    - Allows submission with exceptions if all blockers are resolved or justified.
    - Allows clean submission if no errors or exceptions exist.
    """
    inst = db.get(Institution, institution_id)
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution #{institution_id} not found",
        )

    # 1. Existing submission lifecycle status
    submission = db.scalar(
        select(Submission)
        .options(joinedload(Submission.submitter))
        .where(
            Submission.institution_id == institution_id,
            Submission.academic_year == academic_year,
        )
    )
    current_status = submission.status if submission else SubmissionState.DRAFT.value
    is_locked = current_status in [
        SubmissionState.SUBMITTED.value,
        SubmissionState.SUBMITTED_WITH_EXCEPTIONS.value,
        SubmissionState.UNDER_REVIEW.value,
        SubmissionState.ACCEPTED.value,
        SubmissionState.QUERY_RAISED.value,
        SubmissionState.ESCALATED.value,
    ]

    # 2. Courses and enrolled students
    courses = db.scalars(
        select(Course).where(Course.institution_id == institution_id)
    ).all()
    total_courses = len(courses)

    active_students = db.scalars(
        select(Student)
        .options(joinedload(Student.course))
        .where(
            Student.institution_id == institution_id,
            Student.academic_year == academic_year,
            Student.status.notin_(["withdrawn", "transferred"]),
        )
    ).all()
    total_students = len(active_students)

    students_by_course: dict[int, list[Student]] = {}
    for s in active_students:
        if s.course_id:
            students_by_course.setdefault(s.course_id, []).append(s)

    # 3. Seat declaration reconciliation
    blockers: list[BlockerDetail] = []
    seat_mismatch_detected = False

    for course in courses:
        c_students = students_by_course.get(course.id, [])
        c_reg = sum(1 for s in c_students if s.seat_type == "Regular")
        c_sup = sum(1 for s in c_students if s.seat_type == "Supernumerary")

        decl = db.scalar(
            select(SeatDeclaration).where(
                SeatDeclaration.course_id == course.id,
                SeatDeclaration.academic_year == academic_year,
            )
        )
        if decl is None:
            if len(c_students) > 0:
                seat_mismatch_detected = True
                blockers.append(
                    BlockerDetail(
                        flag_id=None,
                        rule_code="SEAT_DECLARATION_MISMATCH",
                        level="error",
                        message=(
                            f"Course '{course.name}' has {len(c_students)} admitted student(s) "
                            f"but no seat declaration has been saved."
                        ),
                        fix_hint="Navigate to Seat Declarations and enter declared counts.",
                        field="seat_declarations",
                        course_id=course.id,
                        course_name=course.name,
                        target_link="/college/seats",
                        reason="Missing seat declaration for course with enrolled students",
                    )
                )
        else:
            diffs: list[str] = []
            if decl.regular_admitted != c_reg:
                diffs.append(f"regular (declared {decl.regular_admitted} vs actual {c_reg})")
            if decl.supernumerary_admitted != c_sup:
                diffs.append(
                    f"supernumerary (declared {decl.supernumerary_admitted} vs actual {c_sup})"
                )
            if diffs:
                seat_mismatch_detected = True
                blockers.append(
                    BlockerDetail(
                        flag_id=None,
                        rule_code="SEAT_DECLARATION_MISMATCH",
                        level="error",
                        message=(
                            f"Course '{course.name}' declared counts differ from student list: "
                            f"{', '.join(diffs)}."
                        ),
                        fix_hint="Reconcile declared counts on the Seat Declarations page.",
                        field="seat_declarations",
                        course_id=course.id,
                        course_name=course.name,
                        target_link="/college/seats",
                        reason="Declared seat counts differ from enrolled student records",
                    )
                )

    # 4. Institutional validation flags
    flags_stmt = (
        select(ValidationFlag)
        .outerjoin(Student, ValidationFlag.student_id == Student.id)
        .outerjoin(Course, ValidationFlag.course_id == Course.id)
        .outerjoin(Submission, ValidationFlag.submission_id == Submission.id)
        .options(
            joinedload(ValidationFlag.student).joinedload(Student.course),
            joinedload(ValidationFlag.course),
        )
        .where(
            or_(
                Student.institution_id == institution_id,
                Course.institution_id == institution_id,
                Submission.institution_id == institution_id,
            ),
            or_(
                Student.academic_year == academic_year,
                Submission.academic_year == academic_year,
            ),
        )
    )
    flags = db.scalars(flags_stmt).unique().all()

    open_errors_count = 0
    unjustified_exceptions_count = 0
    unjustified_warnings_count = 0
    justified_exceptions_count = 0
    justified_warnings_count = 0

    for fl in flags:
        target_course_id = fl.course_id or (fl.student.course_id if fl.student else None)
        target_course_name = (
            fl.course.name
            if fl.course
            else (fl.student.course.name if fl.student and fl.student.course else None)
        )

        if fl.status == "open":
            if fl.level == "error":
                open_errors_count += 1
                link = (
                    f"/college/students/{fl.student_id}/edit"
                    if fl.student_id
                    else "/college/validation"
                )
                if fl.rule_code == "SEAT_DECLARATION_MISMATCH":
                    seat_mismatch_detected = True
                    link = "/college/seats"
                blockers.append(
                    BlockerDetail(
                        flag_id=fl.id,
                        rule_code=fl.rule_code,
                        level=fl.level,
                        message=fl.message,
                        fix_hint=fl.fix_hint,
                        field=fl.field,
                        student_id=fl.student_id,
                        student_name=fl.student.name if fl.student else None,
                        apaar_id=fl.student.apaar_id if fl.student else None,
                        enrolment_no=fl.student.enrolment_no if fl.student else None,
                        course_id=target_course_id,
                        course_name=target_course_name,
                        target_link=link,
                        reason="Unresolved data error (underlying data must be corrected)",
                    )
                )
            elif fl.level == "exception":
                unjustified_exceptions_count += 1
                blockers.append(
                    BlockerDetail(
                        flag_id=fl.id,
                        rule_code=fl.rule_code,
                        level=fl.level,
                        message=fl.message,
                        fix_hint=fl.fix_hint,
                        field=fl.field,
                        student_id=fl.student_id,
                        student_name=fl.student.name if fl.student else None,
                        apaar_id=fl.student.apaar_id if fl.student else None,
                        enrolment_no=fl.student.enrolment_no if fl.student else None,
                        course_id=target_course_id,
                        course_name=target_course_name,
                        target_link=f"/college/validation?flag_id={fl.id}",
                        reason="Compliance exception requires written justification and evidence",
                    )
                )
            elif fl.level == "warning" and fl.requires_justification:
                unjustified_warnings_count += 1
                blockers.append(
                    BlockerDetail(
                        flag_id=fl.id,
                        rule_code=fl.rule_code,
                        level=fl.level,
                        message=fl.message,
                        fix_hint=fl.fix_hint,
                        field=fl.field,
                        student_id=fl.student_id,
                        student_name=fl.student.name if fl.student else None,
                        apaar_id=fl.student.apaar_id if fl.student else None,
                        enrolment_no=fl.student.enrolment_no if fl.student else None,
                        course_id=target_course_id,
                        course_name=target_course_name,
                        target_link=f"/college/validation?flag_id={fl.id}",
                        reason="Warning requires written justification",
                    )
                )
        elif fl.status == "justified":
            if fl.level == "exception":
                justified_exceptions_count += 1
            elif fl.level == "warning":
                justified_warnings_count += 1

    # 5. Evaluate gate using SubmissionStateMachine
    gate_eval = SubmissionStateMachine.evaluate_gate(
        open_error_count=open_errors_count,
        unjustified_exception_count=unjustified_exceptions_count,
        unjustified_warning_count=unjustified_warnings_count,
        seat_declaration_mismatch=seat_mismatch_detected,
        justified_exception_count=justified_exceptions_count,
        justified_warning_count=justified_warnings_count,
        total_students=total_students,
    )

    can_submit = gate_eval.can_submit and not is_locked
    rec_num = submission.receipt_no if submission and submission.receipt_no else ""
    rec_part = f" (Receipt #{rec_num})" if rec_num else ""
    gate_reason = (
        f"Data for {academic_year} is already submitted and locked{rec_part}."
        if is_locked
        else gate_eval.reason
    )

    submitter_name: str | None = None
    if submission and submission.submitter:
        submitter_name = submission.submitter.email

    return SubmissionGateResponse(
        institution_id=institution_id,
        institution_name=inst.name,
        aicte_id=inst.aicte_id,
        academic_year=academic_year,
        current_status=current_status,
        is_locked=is_locked,
        can_submit=can_submit,
        target_status=gate_eval.target_state.value if gate_eval.target_state else None,
        gate_reason=gate_reason,
        blockers=blockers,
        total_students=total_students,
        total_courses=total_courses,
        open_errors_count=open_errors_count,
        unjustified_exceptions_count=unjustified_exceptions_count,
        unjustified_warnings_count=unjustified_warnings_count,
        justified_exceptions_count=justified_exceptions_count,
        justified_warnings_count=justified_warnings_count,
        seat_mismatch_detected=seat_mismatch_detected,
        submission_id=submission.id if submission else None,
        receipt_no=submission.receipt_no if submission else None,
        submitted_at=submission.submitted_at if submission else None,
        submitted_by_name=submitter_name,
        declaration_ref=submission.declaration_ref if submission else None,
    )


def send_declaration_otp(
    db: Session,
    redis_client: redis.Redis,
    institution_id: int,
    academic_year: str,
    user: User,
) -> SubmissionOtpResponse:
    """Send a mock verification OTP for submission declaration to the user's registered email."""
    inst = db.get(Institution, institution_id)
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution #{institution_id} not found",
        )
    check_institution_can_upload(inst)

    # Check if already submitted/locked
    existing = db.scalar(
        select(Submission).where(
            Submission.institution_id == institution_id,
            Submission.academic_year == academic_year,
        )
    )
    if existing and existing.status in [
        SubmissionState.SUBMITTED.value,
        SubmissionState.SUBMITTED_WITH_EXCEPTIONS.value,
        SubmissionState.UNDER_REVIEW.value,
        SubmissionState.ACCEPTED.value,
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Academic year {academic_year} is already submitted and locked.",
        )

    purpose = f"submission_declaration_{institution_id}_{academic_year}"
    result = store_and_send_otp(
        db=db,
        redis_client=redis_client,
        recipient=user.email,
        channel="email",
        purpose=purpose,
        context=f"Submission declaration for academic year {academic_year}",
    )

    return SubmissionOtpResponse(
        status=result["status"],
        recipient=result["recipient"],
        channel=result["channel"],
        purpose=result["purpose"],
        expires_in=result["expires_in"],
        message=f"Declaration OTP dispatched to {user.email}. Enter the 6-digit code to submit.",
    )


def submit_annual_data(
    db: Session,
    redis_client: redis.Redis,
    institution_id: int,
    user: User,
    payload: SubmissionSubmitRequest,
    client_ip: str = "127.0.0.1",
) -> SubmissionReceiptResponse:
    """Execute final data submission with mock OTP confirmation, locking, and receipt creation.

    Enforces:
    - Only college_admin can execute submission (SPEC.md Section 5 & TASKS.md T23)
    - Active institution approval status (SPEC.md Section 6)
    - Declaration checkbox confirmed
    - Valid OTP from on-file recipient
    - Full submit gate evaluation passes
    - Data becomes locked and read-only (`is_locked=True`)
    - Unique tamper-evident receipt number generated
    - Append-only hash-chained audit log entry written
    """
    if user.role != "college_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only College Administrators (college_admin) are authorized to submit data.",
        )

    inst = db.get(Institution, institution_id)
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution #{institution_id} not found",
        )
    check_institution_can_upload(inst)

    if not payload.confirmed_declaration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must confirm the submission declaration statement before submitting.",
        )

    # 1. Verify OTP code
    purpose = f"submission_declaration_{institution_id}_{payload.academic_year}"
    is_valid, otp_msg, remaining = verify_otp(
        redis_client=redis_client,
        recipient=user.email,
        purpose=purpose,
        code=payload.otp_code,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Declaration OTP verification failed: {otp_msg} ({remaining} tries left)",
        )

    # 2. Re-evaluate gate conditions
    gate = check_submission_gate(
        db=db,
        institution_id=institution_id,
        academic_year=payload.academic_year,
    )
    if not gate.can_submit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Submission gate blocked: {gate.gate_reason}",
        )

    target_state = gate.target_status or SubmissionState.SUBMITTED.value

    # 3. Fetch or instantiate submission record
    submission = db.scalar(
        select(Submission).where(
            Submission.institution_id == institution_id,
            Submission.academic_year == payload.academic_year,
        )
    )
    if not submission:
        submission = Submission(
            institution_id=institution_id,
            academic_year=payload.academic_year,
            status=SubmissionState.DRAFT.value,
        )
        db.add(submission)
        db.flush()

    # Validate state transition
    SubmissionStateMachine.validate_transition(submission.status, target_state)

    # 4. Generate unique receipt number
    clean_year = payload.academic_year.replace("/", "-")
    token = uuid.uuid4().hex[:6].upper()
    receipt_no = f"REC-{clean_year}-{inst.aicte_id}-{token}"

    submitted_at = datetime.now(UTC)
    submission.status = target_state
    submission.submitted_by = user.id
    submission.submitted_at = submitted_at
    submission.receipt_no = receipt_no
    submission.declaration_ref = payload.declaration_text
    db.flush()

    # 5. Lock student records, promote to Central Repository, run cross-checks,
    # dispatch notifications, create review items, and publish SSE events
    from app.submissions.promotion_service import promote_submission_and_run_cross_checks

    promo_result = promote_submission_and_run_cross_checks(
        db=db,
        submission=submission,
        user=user,
        redis_client=redis_client,
        client_ip=client_ip,
    )

    regular_count = promo_result["regular_students"]
    super_count = promo_result["supernumerary_students"]
    final_status = promo_result["status"]

    # 6. Write tamper-evident hash-chained audit log
    audit_service.record(
        db=db,
        actor_id=user.id,
        actor_role=user.role,
        action="submission.submit",
        entity="submission",
        entity_id=str(submission.id),
        before_json={"status": "draft"},
        after_json={
            "status": final_status,
            "receipt_no": receipt_no,
            "total_students": gate.total_students,
            "regular_students": regular_count,
            "supernumerary_students": super_count,
            "justified_exceptions": gate.justified_exceptions_count,
            "declaration_text": payload.declaration_text,
            "duplicates_detected": promo_result["duplicates_detected"],
            "notifications_dispatched": promo_result["notifications_dispatched"],
            "review_items_created": promo_result["review_items_created"],
        },
        ip=client_ip,
    )

    db.commit()

    return SubmissionReceiptResponse(
        institution_id=institution_id,
        institution_name=inst.name,
        aicte_id=inst.aicte_id,
        academic_year=payload.academic_year,
        submission_id=submission.id,
        receipt_no=receipt_no,
        status=final_status,
        submitted_at=submitted_at,
        submitted_by_email=user.email,
        submitted_by_name=user.email,
        declaration_text=payload.declaration_text,
        total_students=gate.total_students,
        regular_students=regular_count,
        supernumerary_students=super_count,
        courses_count=gate.total_courses,
        justified_exceptions_count=gate.justified_exceptions_count,
        is_locked=True,
    )


def get_submission_receipt(
    db: Session,
    institution_id: int,
    academic_year: str = "2026-27",
) -> SubmissionReceiptResponse:
    """Retrieve official submission receipt details for an already submitted academic year."""
    inst = db.get(Institution, institution_id)
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution #{institution_id} not found",
        )

    submission = db.scalar(
        select(Submission)
        .options(joinedload(Submission.submitter))
        .where(
            Submission.institution_id == institution_id,
            Submission.academic_year == academic_year,
        )
    )
    if not submission or submission.status == SubmissionState.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No finalized submission found for academic year {academic_year}",
        )

    students = db.scalars(
        select(Student).where(
            Student.institution_id == institution_id,
            Student.academic_year == academic_year,
            Student.status.notin_(["withdrawn", "transferred"]),
        )
    ).all()

    regular_count = sum(1 for s in students if s.seat_type == "Regular")
    super_count = sum(1 for s in students if s.seat_type == "Supernumerary")

    courses_count = (
        db.scalar(
            select(func.count(Course.id)).where(Course.institution_id == institution_id)
        )
        or 0
    )

    justified_count = (
        db.scalar(
            select(func.count(ValidationFlag.id))
            .outerjoin(Student, ValidationFlag.student_id == Student.id)
            .outerjoin(Course, ValidationFlag.course_id == Course.id)
            .outerjoin(Submission, ValidationFlag.submission_id == Submission.id)
            .where(
                or_(
                    Student.institution_id == institution_id,
                    Course.institution_id == institution_id,
                    Submission.institution_id == institution_id,
                ),
                or_(
                    Student.academic_year == academic_year,
                    Submission.academic_year == academic_year,
                ),
                ValidationFlag.status == "justified",
            )
        )
        or 0
    )

    return SubmissionReceiptResponse(
        institution_id=institution_id,
        institution_name=inst.name,
        aicte_id=inst.aicte_id,
        academic_year=academic_year,
        submission_id=submission.id,
        receipt_no=submission.receipt_no or "N/A",
        status=submission.status,
        submitted_at=submission.submitted_at or datetime.now(UTC),
        submitted_by_email=submission.submitter.email if submission.submitter else "system",
        submitted_by_name=submission.submitter.email if submission.submitter else "system",
        declaration_text=submission.declaration_ref or "Declaration on file",
        total_students=len(students),
        regular_students=regular_count,
        supernumerary_students=super_count,
        courses_count=courses_count,
        justified_exceptions_count=justified_count,
        is_locked=True,
    )
