"""Validation engine high-level integration services and persistence entry points."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth.security import decrypt_dob
from app.integrations.factory import get_apaar_client
from app.integrations.interfaces import ApaarClient
from app.models import (
    AnomalyScore,
    Course,
    CourseIntake,
    SeatDeclaration,
    Student,
    Submission,
    ValidationFlag,
)
from app.students.duplicate_service import query_duplicates_by_apaar_and_year
from app.validation.codes import (
    INTAKE_EXCEEDED,
    SEAT_DECLARATION_MISMATCH,
    SUPERNUMERARY_EXCEEDED,
)
from app.validation.context import ValidationContext
from app.validation.engine import run_rules
from app.validation.flags import Flag, ValidationLevel, ValidationResult, ValidationScope

COURSE_LEVEL_RULES = {
    INTAKE_EXCEEDED,
    SUPERNUMERARY_EXCEEDED,
    SEAT_DECLARATION_MISMATCH,
}


def student_model_to_row(student: Student, row_number: int | None = None) -> dict[str, Any]:
    """Convert an ORM Student model into canonical dictionary format for validation."""
    dob_val: str | None = None
    if student.dob_encrypted:
        try:
            d = decrypt_dob(student.dob_encrypted)
            dob_val = d.isoformat()
        except Exception:
            dob_val = student.dob_encrypted

    course_name = student.course.name if student.course else ""
    branch_name = student.course.branch if student.course else ""

    adm_date_str = (
        student.admission_date.isoformat()
        if hasattr(student.admission_date, "isoformat")
        else str(student.admission_date)
    )

    return {
        "apaar_id": student.apaar_id,
        "name": student.name,
        "dob": dob_val,
        "gender": student.gender,
        "course": course_name,
        "branch": branch_name,
        "admission_year": student.academic_year,
        "enrolment_no": student.enrolment_no,
        "admission_date": adm_date_str,
        "admission_mode": student.admission_mode,
        "seat_type": student.seat_type,
        "reservation_category": student.reservation_category,
        "nri": student.nri,
        "oci": student.oci,
        "foreign_national": student.foreign_national,
        "country": student.fn_country or "",
        # Metadata keys for referencing and persistence
        "id": student.id,
        "student_id": student.id,
        "course_id": student.course_id,
        "institution_id": student.institution_id,
        "submission_id": student.submission_id,
        "row_number": row_number if row_number is not None else student.id,
        "status": student.status,
    }


def persist_validation_flags(
    db: Session,
    flags: ValidationResult | Sequence[Flag],
    submission_id: int | None = None,
    course_id: int | None = None,
    institution_id: int | None = None,
    student_mapping: dict[Any, Student] | None = None,
    keep_justifications: bool = True,
    update_student_status: bool = True,
) -> list[ValidationFlag]:
    """Persist generated validation flags into the database with row references.

    Guarantees:
    - Idempotent re-run: re-running does not duplicate flags.
    - Valid justifications are preserved on still-valid flags.
    - Flags that no longer fire are transitioned to 'resolved' status.
    - Associates flags with student_id, course_id, and submission_id.
    - Automatically updates student status to 'flagged' or 'valid' based on active flags.
    """
    mapping: dict[Any, Student] = student_mapping or {}

    s_ids: list[int] = []
    if mapping:
        s_ids = [
            s.id if hasattr(s, "id") else s
            for s in mapping.values()
            if (hasattr(s, "id") and getattr(s, "id") is not None) or isinstance(s, int)
        ]

    # Query existing flags in this scope
    stmt = select(ValidationFlag).options(selectinload(ValidationFlag.justifications))
    if submission_id is not None:
        stmt = stmt.where(ValidationFlag.submission_id == submission_id)
    elif course_id is not None:
        if s_ids:
            stmt = stmt.where(
                or_(
                    ValidationFlag.course_id == course_id,
                    ValidationFlag.student_id.in_(s_ids),
                )
            )
        else:
            stmt = stmt.where(ValidationFlag.course_id == course_id)
    elif s_ids:
        stmt = stmt.where(ValidationFlag.student_id.in_(s_ids))
    elif institution_id is not None:
        stmt = (
            stmt.outerjoin(Student, ValidationFlag.student_id == Student.id)
            .outerjoin(Course, ValidationFlag.course_id == Course.id)
            .outerjoin(Submission, ValidationFlag.submission_id == Submission.id)
            .where(
                or_(
                    Student.institution_id == institution_id,
                    Course.institution_id == institution_id,
                    Submission.institution_id == institution_id,
                )
            )
        )
    elif mapping:
        s_ids = [s.id for s in mapping.values() if getattr(s, "id", None) is not None]
        if s_ids:
            stmt = stmt.where(ValidationFlag.student_id.in_(s_ids))
        else:
            stmt = stmt.where(ValidationFlag.id == -1)
    else:
        # Default query for institution scope if available
        stmt = stmt.where(ValidationFlag.id == -1)

    existing_rows = db.scalars(stmt).unique().all()

    # Index existing flags by (student_id, course_id, rule_code, field)
    existing_map: dict[tuple[int | None, int | None, str, str | None], list[ValidationFlag]] = {}
    for fl in existing_rows:
        k = (fl.student_id, fl.course_id, fl.rule_code, fl.field)
        existing_map.setdefault(k, []).append(fl)

    matched_flag_ids: set[int] = set()
    persisted: list[ValidationFlag] = []

    for flag in flags:
        # Determine target student_id, course_id, submission_id
        target_student_id: int | None = None
        target_course_id: int | None = None
        target_submission_id: int | None = submission_id

        # Check if row_ref maps to a student
        if flag.row_ref in mapping:
            st = mapping[flag.row_ref]
            target_student_id = getattr(st, "id", st if isinstance(st, int) else None)
            target_course_id = (
                getattr(st, "course_id", None) if not isinstance(st, int) else None
            ) or course_id
            target_submission_id = (
                getattr(st, "submission_id", None) if not isinstance(st, int) else None
            ) or submission_id
        elif isinstance(flag.row_ref, int) and flag.row_ref in [
            s.id for s in mapping.values() if getattr(s, "id", None)
        ]:
            target_student_id = flag.row_ref
            st = next(s for s in mapping.values() if s.id == flag.row_ref)
            target_course_id = getattr(st, "course_id", None) or course_id
            target_submission_id = getattr(st, "submission_id", None) or submission_id
        elif flag.rule_code in COURSE_LEVEL_RULES or flag.rule_code.startswith("ANOM_"):
            target_student_id = None
            target_course_id = flag.row_ref if isinstance(flag.row_ref, int) else course_id
            target_submission_id = submission_id
        else:
            # Row level fallback when row_ref is student integer id
            if isinstance(flag.row_ref, int) and flag.row_ref > 0:
                target_student_id = flag.row_ref
            target_course_id = course_id
            target_submission_id = submission_id

        composite_key = (target_student_id, target_course_id, flag.rule_code, flag.field)
        matched_existing: ValidationFlag | None = None

        if composite_key in existing_map and existing_map[composite_key]:
            # Pop first matching existing flag
            matched_existing = existing_map[composite_key].pop(0)
        elif target_student_id is not None:
            for k in list(existing_map.keys()):
                if (
                    k[0] == target_student_id
                    and k[2] == flag.rule_code
                    and k[3] == flag.field
                    and existing_map[k]
                ):
                    matched_existing = existing_map[k].pop(0)
                    break

        if matched_existing is not None:
            matched_flag_ids.add(matched_existing.id)

            # Idempotent re-run: Keep justification if present
            has_justification = (
                len(matched_existing.justifications) > 0
                or matched_existing.status == "justified"
            )
            if keep_justifications and has_justification:
                matched_existing.status = "justified"
            elif matched_existing.status == "resolved":
                matched_existing.status = "open"  # Re-open if condition still exists

            # Update mutable metadata
            matched_existing.message = flag.message
            matched_existing.fix_hint = flag.fix_hint
            matched_existing.level = (
                flag.level.value if isinstance(flag.level, ValidationLevel) else str(flag.level)
            )
            matched_existing.audience = (
                flag.audience.value
                if hasattr(flag.audience, "value")
                else str(flag.audience)
            )
            matched_existing.requires_justification = flag.requires_justification
            if target_submission_id is not None:
                matched_existing.submission_id = target_submission_id
            if target_course_id is not None:
                matched_existing.course_id = target_course_id

            persisted.append(matched_existing)
        else:
            # Create new flag record
            level_str = (
                flag.level.value if isinstance(flag.level, ValidationLevel) else str(flag.level)
            )
            aud_str = (
                flag.audience.value
                if hasattr(flag.audience, "value")
                else str(flag.audience)
            )
            new_fl = ValidationFlag(
                student_id=target_student_id,
                course_id=target_course_id,
                submission_id=target_submission_id,
                rule_code=flag.rule_code,
                level=level_str,
                field=flag.field,
                message=flag.message,
                fix_hint=flag.fix_hint,
                audience=aud_str,
                requires_justification=flag.requires_justification,
                status="open",
            )
            db.add(new_fl)
            persisted.append(new_fl)

    # Resolve any remaining existing flags that were not re-emitted
    for fl_list in existing_map.values():
        for old_fl in fl_list:
            if old_fl.id not in matched_flag_ids and old_fl.status in ("open", "justified"):
                old_fl.status = "resolved"

    db.flush()

    # Update student statuses if requested
    if update_student_status and mapping:
        active_flag_student_ids = {
            f.student_id
            for f in persisted
            if f.student_id is not None and f.status != "resolved"
        }
        for st in mapping.values():
            if not hasattr(st, "status") or not hasattr(st, "id"):
                continue
            if st.status in ("draft", "valid", "flagged"):
                if st.id in active_flag_student_ids:
                    st.status = "flagged"
                else:
                    st.status = "valid"

        db.flush()

    return persisted


def validate_rows(
    rows: list[dict[str, Any]] | list[Student] | dict[str, Any] | Student,
    institution_id: int | None = None,
    academic_year: str | None = None,
    course_id: int | None = None,
    submission_id: int | None = None,
    db_session: Session | None = None,
    overrides: dict[str, Any] | None = None,
    scope: ValidationScope | str | None = None,
    apaar_client: ApaarClient | None = None,
    persist: bool = False,
    keep_justifications: bool = True,
    context: ValidationContext | None = None,
) -> ValidationResult:
    """Validate a collection of student rows or Student models.

    Per SPEC.md Section 9.4:
    - Runs cheap checks first: file, field, APAAR, row consistency, duplicates.
    - Supports single student entry, CSV rows, and Student ORM models.
    - Idempotently persists flags when persist=True and db_session is provided.
    """
    # 1. Normalize input rows
    raw_list: list[Any] = []
    if isinstance(rows, (list, tuple)):
        raw_list = list(rows)
    else:
        raw_list = [rows]

    normalized_rows: list[dict[str, Any]] = []
    student_mapping: dict[Any, Student] = {}

    for idx, item in enumerate(raw_list, start=1):
        if isinstance(item, Student):
            row_dict = student_model_to_row(item, row_number=idx)
            normalized_rows.append(row_dict)
            student_mapping[idx] = item
            student_mapping[item.id] = item
            student_mapping[item.apaar_id] = item
            if institution_id is None:
                institution_id = item.institution_id
            if academic_year is None:
                academic_year = item.academic_year
            if course_id is None:
                course_id = item.course_id
            if submission_id is None:
                submission_id = item.submission_id
        elif isinstance(item, dict):
            row_copy = dict(item)
            if "row_number" not in row_copy:
                row_copy["row_number"] = idx
            normalized_rows.append(row_copy)
            # Map by student_id or apaar_id if available
            sid = row_copy.get("student_id") or row_copy.get("id")
            if sid:
                student_mapping[idx] = sid  # type: ignore[assignment]
                student_mapping[sid] = sid  # type: ignore[assignment]
        else:
            raise TypeError(f"Unsupported row item type: {type(item)}")

    # 2. Build or complete ValidationContext
    if context is not None:
        val_ctx = context
        if normalized_rows and not val_ctx.rows:
            val_ctx.rows = normalized_rows
    else:
        client = apaar_client
        if client is None and db_session is not None:
            client = get_apaar_client(db_session)

        # Cross-college duplicate lookup if db_session and academic_year available
        cross_college: list[Any] = []
        if db_session is not None and academic_year:
            apaar_ids = [r.get("apaar_id") for r in normalized_rows if r.get("apaar_id")]
            if apaar_ids:
                cross_college = query_duplicates_by_apaar_and_year(
                    db_session,
                    apaar_ids,
                    academic_year,
                    exclude_institution_id=institution_id,
                )

        extra_ctx: dict[str, Any] = {"db": db_session}
        if db_session is not None and institution_id is not None:
            extra_ctx["approved_courses"] = list(
                db_session.scalars(
                    select(Course).where(Course.institution_id == institution_id)
                ).all()
            )

        val_ctx = ValidationContext(
            rows=normalized_rows,
            institution_id=institution_id,
            academic_year=academic_year,
            course_id=course_id,
            submission_id=submission_id,
            apaar_client=client,
            db_session=db_session,
            other_college_students=cross_college,
            extra=extra_ctx,
        )

    # 3. Execute engine rules
    result = run_rules(
        val_ctx,
        scope=scope,
        overrides=overrides,
        db_session=db_session,
    )

    # 4. Persist flags if requested
    if persist and db_session is not None:
        persist_validation_flags(
            db=db_session,
            flags=result,
            submission_id=submission_id,
            course_id=course_id,
            institution_id=institution_id,
            student_mapping=student_mapping,
            keep_justifications=keep_justifications,
        )

    return result


def validate_course(
    institution_id: int,
    course_id: int,
    academic_year: str,
    db_session: Session | None = None,
    submission_id: int | None = None,
    rows: list[dict[str, Any]] | list[Student] | None = None,
    declared_seats: dict[str, int] | SeatDeclaration | None = None,
    persist: bool = False,
    overrides: dict[str, Any] | None = None,
    apaar_client: ApaarClient | None = None,
    keep_justifications: bool = True,
) -> ValidationResult:
    """Validate a single course's student enrolments, quotas, and declared seats."""
    student_mapping: dict[Any, Student] = {}
    normalized_rows: list[dict[str, Any]] = []

    # 1. Resolve student rows
    if rows is not None:
        for idx, item in enumerate(rows, start=1):
            if isinstance(item, Student):
                r = student_model_to_row(item, row_number=idx)
                normalized_rows.append(r)
                student_mapping[idx] = item
                student_mapping[item.id] = item
                student_mapping[item.apaar_id] = item
            elif isinstance(item, dict):
                r = dict(item)
                if "row_number" not in r:
                    r["row_number"] = idx
                normalized_rows.append(r)
    elif db_session is not None:
        students = db_session.scalars(
            select(Student)
            .options(joinedload(Student.course))
            .where(
                Student.institution_id == institution_id,
                Student.course_id == course_id,
                Student.academic_year == academic_year,
            )
        ).all()
        for idx, st in enumerate(students, start=1):
            r = student_model_to_row(st, row_number=idx)
            normalized_rows.append(r)
            student_mapping[idx] = st
            student_mapping[st.id] = st
            student_mapping[st.apaar_id] = st

    # 2. Resolve course, intake, and seat declaration
    course_obj: Course | None = None
    approved_intake: int | None = None
    approved_supernumerary: int | None = None
    declared_dict: dict[str, int] | None = None

    if db_session is not None:
        course_obj = db_session.get(Course, course_id)
        intake_rec = db_session.scalar(
            select(CourseIntake).where(
                CourseIntake.course_id == course_id,
                CourseIntake.academic_year == academic_year,
            )
        )
        if intake_rec:
            approved_intake = intake_rec.approved_intake
            approved_supernumerary = intake_rec.supernumerary_seats_allowed

        if declared_seats is None:
            decl_rec = db_session.scalar(
                select(SeatDeclaration).where(
                    SeatDeclaration.course_id == course_id,
                    SeatDeclaration.academic_year == academic_year,
                )
            )
            if decl_rec:
                declared_dict = {
                    "regular_admitted": decl_rec.regular_admitted,
                    "supernumerary_admitted": decl_rec.supernumerary_admitted,
                    "nri_count": decl_rec.nri_count,
                    "oci_count": decl_rec.oci_count,
                    "fn_count": decl_rec.fn_count,
                }
        elif isinstance(declared_seats, SeatDeclaration):
            declared_dict = {
                "regular_admitted": declared_seats.regular_admitted,
                "supernumerary_admitted": declared_seats.supernumerary_admitted,
                "nri_count": declared_seats.nri_count,
                "oci_count": declared_seats.oci_count,
                "fn_count": declared_seats.fn_count,
            }
        elif isinstance(declared_seats, dict):
            declared_dict = declared_seats

    # 3. Cross-college duplicates
    cross_college: list[Any] = []
    if db_session is not None:
        apaar_ids = [r.get("apaar_id") for r in normalized_rows if r.get("apaar_id")]
        if apaar_ids:
            cross_college = query_duplicates_by_apaar_and_year(
                db_session,
                apaar_ids,
                academic_year,
                exclude_institution_id=institution_id,
            )

    client = apaar_client or (get_apaar_client(db_session) if db_session else None)

    context = ValidationContext(
        rows=normalized_rows,
        institution_id=institution_id,
        course_id=course_id,
        course=course_obj,
        academic_year=academic_year,
        submission_id=submission_id,
        approved_intake=approved_intake,
        approved_supernumerary=approved_supernumerary,
        declared_seats=declared_dict,
        other_college_students=cross_college,
        apaar_client=client,
        db_session=db_session,
        extra={
            "course_intakes": {course_id: approved_intake} if approved_intake is not None else {},
            "approved_courses": {course_id: course_obj} if course_obj else {},
        },
    )

    result = run_rules(context, overrides=overrides, db_session=db_session)

    if persist and db_session is not None:
        persist_validation_flags(
            db=db_session,
            flags=result,
            submission_id=submission_id,
            course_id=course_id,
            institution_id=institution_id,
            student_mapping=student_mapping,
            keep_justifications=keep_justifications,
        )

    return result


def validate_submission(
    submission_id: int | None = None,
    institution_id: int | None = None,
    academic_year: str | None = None,
    db_session: Session | None = None,
    persist: bool = True,
    overrides: dict[str, Any] | None = None,
    apaar_client: ApaarClient | None = None,
    keep_justifications: bool = True,
) -> ValidationResult:
    """Validate an entire institutional submission across all courses, seat declarations,
    and student records.

    Per SPEC.md Section 9.4 & 10:
    - Runs all file, row, course, and cross-college rules.
    - Idempotently updates flags while preserving existing justifications.
    - Updates student statuses ('flagged' or 'valid').
    """
    if db_session is None:
        raise ValueError("db_session is required for validate_submission")

    sub_record: Submission | None = None
    if submission_id is not None:
        sub_record = db_session.get(Submission, submission_id)
        if sub_record:
            institution_id = sub_record.institution_id
            academic_year = sub_record.academic_year
    elif institution_id is not None and academic_year is not None:
        sub_record = db_session.scalar(
            select(Submission).where(
                Submission.institution_id == institution_id,
                Submission.academic_year == academic_year,
            )
        )
        if sub_record:
            submission_id = sub_record.id

    if institution_id is None or academic_year is None:
        raise ValueError(
            "institution_id and academic_year must be provided or resolvable from submission_id"
        )

    # 1. Load all courses for this institution
    courses = db_session.scalars(
        select(Course).where(Course.institution_id == institution_id)
    ).all()
    course_ids = [c.id for c in courses]
    courses_by_id = {c.id: c for c in courses}
    courses_by_name = {c.name.strip().lower(): c for c in courses}

    # 2. Load all intakes for these courses in this academic year
    intakes = db_session.scalars(
        select(CourseIntake).where(
            CourseIntake.course_id.in_(course_ids),
            CourseIntake.academic_year == academic_year,
        )
    ).all()
    intakes_by_course = {ci.course_id: ci for ci in intakes}

    # 3. Load all seat declarations
    declarations = db_session.scalars(
        select(SeatDeclaration).where(
            SeatDeclaration.course_id.in_(course_ids),
            SeatDeclaration.academic_year == academic_year,
        )
    ).all()
    declarations_by_course = {sd.course_id: sd for sd in declarations}

    # 4. Load all active students for this institution & academic year
    students = db_session.scalars(
        select(Student)
        .options(joinedload(Student.course))
        .where(
            Student.institution_id == institution_id,
            Student.academic_year == academic_year,
        )
    ).all()

    student_mapping: dict[Any, Student] = {}
    all_rows: list[dict[str, Any]] = []
    apaar_ids: list[str] = []

    for idx, st in enumerate(students, start=1):
        r = student_model_to_row(st, row_number=idx)
        all_rows.append(r)
        student_mapping[idx] = st
        student_mapping[st.id] = st
        student_mapping[st.apaar_id] = st
        if st.apaar_id:
            apaar_ids.append(st.apaar_id)

    # 5. Cross-college duplicates
    cross_college = query_duplicates_by_apaar_and_year(
        db_session,
        apaar_ids,
        academic_year,
        exclude_institution_id=institution_id,
    )

    client = apaar_client or get_apaar_client(db_session)

    # 6. Load any pre-computed anomaly scores and build validation context
    anomaly_scores_by_course: dict[int, AnomalyScore] = {}
    if db_session is not None:
        db_anom_records = db_session.scalars(
            select(AnomalyScore).where(
                AnomalyScore.institution_id == institution_id,
                AnomalyScore.academic_year == academic_year,
            )
        ).all()
        for rec in db_anom_records:
            anomaly_scores_by_course[rec.course_id] = rec

    context = ValidationContext(
        rows=all_rows,
        institution_id=institution_id,
        academic_year=academic_year,
        submission_id=submission_id,
        other_college_students=cross_college,
        apaar_client=client,
        db_session=db_session,
        extra={
            "courses_by_id": courses_by_id,
            "approved_courses": courses_by_name,
            "course_intakes": intakes_by_course,
            "seat_declarations": declarations_by_course,
            "anomaly_scores": anomaly_scores_by_course,
        },
    )

    # 7. Run validation rules
    result = run_rules(context, overrides=overrides, db_session=db_session)

    # 8. Idempotently persist flags
    if persist:
        persist_validation_flags(
            db=db_session,
            flags=result,
            submission_id=submission_id,
            institution_id=institution_id,
            student_mapping=student_mapping,
            keep_justifications=keep_justifications,
        )

    return result
