"""Shared helpers for course-level validation rules and seat reconciliation.

Supports:
- INTAKE_EXCEEDED
- SUPERNUMERARY_EXCEEDED
- SEAT_DECLARATION_MISMATCH

Handles student counting by seat_type, category flags, course resolution,
quota resolution, and exclusion of withdrawn/transferred students.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.models import Course, CourseIntake, SeatDeclaration
from app.validation.context import ValidationContext


@dataclass
class CourseStudentCounts:
    """Aggregated seat and category statistics for an enrolled course."""

    course_name: str | None = None
    course_branch: str | None = None
    course_id: Any | None = None
    regular_count: int = 0
    supernumerary_count: int = 0
    nri_count: int = 0
    oci_count: int = 0
    fn_count: int = 0
    total_count: int = 0
    active_rows: list[Any] = field(default_factory=list)


def is_active_student(row: Any, context: ValidationContext) -> bool:
    """Check if a student record is active (not withdrawn or transferred)."""
    status = context.get_field_value(row, "status")
    if status is None:
        return True
    return str(status).strip().lower() not in ("withdrawn", "transferred")


def get_course_student_counts(context: ValidationContext) -> dict[str, CourseStudentCounts]:
    """Aggregate active student records grouped by course.

    Excludes withdrawn and transferred students.
    De-duplicates between context.rows and context.all_college_students.
    """
    groups: dict[str, CourseStudentCounts] = {}
    seen_apaars: set[str] = set()

    # Process uploaded/draft rows first
    for row in context.get_all_rows():
        if not is_active_student(row, context):
            continue

        apaar = context.get_field_value(row, "apaar_id")
        if apaar:
            seen_apaars.add(str(apaar).strip())

        _aggregate_row(row, context, groups)

    # Process persisted all_college_students if provided, skipping already seen APAARs
    if context.all_college_students:
        for row in context.all_college_students:
            if not is_active_student(row, context):
                continue

            apaar = context.get_field_value(row, "apaar_id")
            if apaar and str(apaar).strip() in seen_apaars:
                continue

            # Check academic year filter if provided on context
            if context.academic_year:
                row_year = context.get_field_value(row, "academic_year")
                if row_year and str(row_year).strip() != str(context.academic_year).strip():
                    continue

            # Check institution filter if provided on context
            if context.institution_id is not None:
                row_inst = context.get_field_value(row, "institution_id")
                if row_inst is not None and row_inst != context.institution_id:
                    continue

            if apaar:
                seen_apaars.add(str(apaar).strip())

            _aggregate_row(row, context, groups)

    # If context has no rows but has course and declared_seats, create empty default group
    if not groups and (context.course is not None or context.approved_intake is not None):
        course_name = None
        course_branch = None
        course_id = None
        if context.course is not None:
            c = context.course
            course_name = getattr(c, "name", None) if not isinstance(c, dict) else c.get("name")
            course_branch = (
                getattr(c, "branch", None) if not isinstance(c, dict) else c.get("branch")
            )
            course_id = getattr(c, "id", None) if not isinstance(c, dict) else c.get("id")

        groups["default"] = CourseStudentCounts(
            course_name=course_name,
            course_branch=course_branch,
            course_id=course_id,
        )

    return groups


def _aggregate_row(
    row: Any, context: ValidationContext, groups: dict[str, CourseStudentCounts]
) -> None:
    """Add a student row to the appropriate course group."""
    row_course = context.get_field_value(row, "course") or context.get_field_value(
        row, "course_name"
    )
    row_branch = context.get_field_value(row, "branch")
    row_course_id = context.get_field_value(row, "course_id")

    # Determine group key
    if row_course_id is not None:
        group_key = f"id:{row_course_id}"
    elif row_course is not None:
        c_name = str(row_course).strip().lower()
        b_name = str(row_branch or "").strip().lower()
        group_key = f"name:{c_name}|branch:{b_name}"
    elif context.course is not None:
        c = context.course
        cid = getattr(c, "id", None) if not isinstance(c, dict) else c.get("id")
        cname = getattr(c, "name", None) if not isinstance(c, dict) else c.get("name")
        group_key = f"id:{cid}" if cid is not None else f"name:{cname}"
    else:
        group_key = "default"

    if group_key not in groups:
        course_name = row_course
        course_branch = row_branch
        course_id = row_course_id
        if course_name is None and context.course is not None:
            c = context.course
            course_name = getattr(c, "name", None) if not isinstance(c, dict) else c.get("name")
            course_branch = (
                getattr(c, "branch", None) if not isinstance(c, dict) else c.get("branch")
            )
            course_id = getattr(c, "id", None) if not isinstance(c, dict) else c.get("id")

        groups[group_key] = CourseStudentCounts(
            course_name=course_name,
            course_branch=course_branch,
            course_id=course_id,
        )

    counts = groups[group_key]
    counts.active_rows.append(row)
    counts.total_count += 1

    # Seat type classification: Regular vs Supernumerary
    seat_type = context.get_field_value(row, "seat_type")
    if seat_type and str(seat_type).strip().lower() == "supernumerary":
        counts.supernumerary_count += 1
    else:
        counts.regular_count += 1

    # Category counts
    nri = context.get_field_value(row, "nri")
    if nri and str(nri).strip().lower() in ("yes", "y", "true", "1"):
        counts.nri_count += 1

    oci = context.get_field_value(row, "oci")
    if oci and str(oci).strip().lower() in ("yes", "y", "true", "1"):
        counts.oci_count += 1

    fn = context.get_field_value(row, "foreign_national")
    if fn and str(fn).strip().lower() in ("yes", "y", "true", "1"):
        counts.fn_count += 1


def resolve_approved_intake(
    counts: CourseStudentCounts, context: ValidationContext
) -> int | None:
    """Resolve approved intake for a course from context, parameters, or database."""
    # 1. Direct param override
    param_intake = context.get_param("approved_intake")
    if param_intake is not None:
        return int(param_intake)

    # 2. Direct context approved_intake
    if context.approved_intake is not None:
        return int(context.approved_intake)

    # 3. Context course object
    if context.course is not None:
        c = context.course
        if hasattr(c, "approved_intake"):
            return int(c.approved_intake)
        if isinstance(c, dict) and "approved_intake" in c:
            return int(c["approved_intake"])

    # 4. Extra course intakes map
    course_intakes = context.extra.get("course_intakes")
    if course_intakes and isinstance(course_intakes, dict):
        if counts.course_id in course_intakes:
            val = course_intakes[counts.course_id]
            return _extract_intake_number(val, "approved_intake")
        if counts.course_name in course_intakes:
            val = course_intakes[counts.course_name]
            return _extract_intake_number(val, "approved_intake")
        key = (counts.course_name, counts.course_branch)
        if key in course_intakes:
            val = course_intakes[key]
            return _extract_intake_number(val, "approved_intake")

    # 5. Extra approved_courses list
    approved_courses = context.extra.get("approved_courses")
    if approved_courses:
        for appr in approved_courses:
            if _match_course_ref(counts, appr):
                if hasattr(appr, "approved_intake"):
                    return int(appr.approved_intake)
                if isinstance(appr, dict) and "approved_intake" in appr:
                    return int(appr["approved_intake"])

    # 6. Database lookup
    if context.db_session is not None:
        academic_year = context.academic_year or _find_academic_year(counts, context)
        if academic_year:
            intake_rec = _lookup_course_intake_db(counts, academic_year, context)
            if intake_rec is not None:
                return int(intake_rec.approved_intake)

    return None


def resolve_approved_supernumerary(
    counts: CourseStudentCounts, context: ValidationContext
) -> int | None:
    """Resolve approved supernumerary quota for a course from context, parameters, or DB."""
    # 1. Parameter overrides
    param_super = context.get_param("approved_supernumerary")
    if param_super is None:
        param_super = context.get_param("supernumerary_seats_allowed")
    if param_super is not None:
        return int(param_super)

    # 2. Direct context approved_supernumerary
    if context.approved_supernumerary is not None:
        return int(context.approved_supernumerary)

    # 3. Context course object
    if context.course is not None:
        c = context.course
        if hasattr(c, "supernumerary_seats_allowed"):
            return int(c.supernumerary_seats_allowed)
        if isinstance(c, dict) and "supernumerary_seats_allowed" in c:
            return int(c["supernumerary_seats_allowed"])
        if hasattr(c, "supernumerary_allowed") and not c.supernumerary_allowed:
            return 0
        if isinstance(c, dict) and "supernumerary_allowed" in c and not c["supernumerary_allowed"]:
            return 0

    # 4. Extra course intakes/supernumerary map
    course_intakes = context.extra.get("course_intakes")
    if course_intakes and isinstance(course_intakes, dict):
        refs = (
            counts.course_id,
            counts.course_name,
            (counts.course_name, counts.course_branch),
        )
        for ref in refs:
            if ref in course_intakes:
                val = course_intakes[ref]
                extracted = _extract_intake_number(val, "supernumerary_seats_allowed")
                if extracted is not None:
                    return extracted

    # 5. Extra approved_courses list
    approved_courses = context.extra.get("approved_courses")
    if approved_courses:
        for appr in approved_courses:
            if _match_course_ref(counts, appr):
                if hasattr(appr, "supernumerary_seats_allowed"):
                    return int(appr.supernumerary_seats_allowed)
                if isinstance(appr, dict) and "supernumerary_seats_allowed" in appr:
                    return int(appr["supernumerary_seats_allowed"])
                if hasattr(appr, "supernumerary_allowed") and not appr.supernumerary_allowed:
                    return 0
                if (
                    isinstance(appr, dict)
                    and "supernumerary_allowed" in appr
                    and not appr["supernumerary_allowed"]
                ):
                    return 0

    # 6. Database lookup
    if context.db_session is not None:
        academic_year = context.academic_year or _find_academic_year(counts, context)
        if academic_year:
            intake_rec = _lookup_course_intake_db(counts, academic_year, context)
            if intake_rec is not None:
                return int(intake_rec.supernumerary_seats_allowed)

    return None


def resolve_declared_seats(
    counts: CourseStudentCounts, context: ValidationContext
) -> dict[str, int] | None:
    """Resolve college-declared seats for a course from context, parameters, or DB."""
    # 1. Parameter overrides
    param_decl = context.get_param("declared_seats")
    if param_decl is not None:
        return _normalize_declaration(param_decl, counts)

    # 2. Direct context declared_seats
    if context.declared_seats is not None:
        return _normalize_declaration(context.declared_seats, counts)

    # 3. Extra seat_declaration
    extra_decl = context.extra.get("seat_declaration")
    if extra_decl is not None:
        return _normalize_declaration(extra_decl, counts)

    # 4. Database lookup
    if context.db_session is not None:
        academic_year = context.academic_year or _find_academic_year(counts, context)
        if academic_year:
            decl_model = _lookup_seat_declaration_db(counts, academic_year, context)
            if decl_model is not None:
                return _normalize_declaration(decl_model, counts)

    return None


def _normalize_declaration(decl: Any, counts: CourseStudentCounts) -> dict[str, int] | None:
    """Normalize a SeatDeclaration model, dict, or nested map into a single course declaration."""
    if decl is None:
        return None

    # If decl is a dict keyed by course id / name / tuple
    if isinstance(decl, dict):
        if counts.course_id is not None and counts.course_id in decl:
            return _normalize_declaration(decl[counts.course_id], counts)
        if counts.course_name is not None and counts.course_name in decl:
            return _normalize_declaration(decl[counts.course_name], counts)
        key = (counts.course_name, counts.course_branch)
        if key in decl:
            return _normalize_declaration(decl[key], counts)

    result: dict[str, int] = {}

    def extract_val(field_names: list[str]) -> int | None:
        for fname in field_names:
            if isinstance(decl, dict):
                if fname in decl and decl[fname] is not None:
                    return int(decl[fname])
            else:
                if hasattr(decl, fname):
                    val = getattr(decl, fname)
                    if val is not None:
                        return int(val)
        return None

    reg = extract_val(["regular_admitted", "regular"])
    if reg is not None:
        result["regular_admitted"] = reg

    sup = extract_val(["supernumerary_admitted", "supernumerary"])
    if sup is not None:
        result["supernumerary_admitted"] = sup

    nri = extract_val(["nri_count", "nri"])
    if nri is not None:
        result["nri_count"] = nri

    oci = extract_val(["oci_count", "oci"])
    if oci is not None:
        result["oci_count"] = oci

    fn = extract_val(["fn_count", "foreign_national", "fn"])
    if fn is not None:
        result["fn_count"] = fn

    return result if result else None


def _extract_intake_number(val: Any, target_field: str) -> int | None:
    """Extract integer quota from an int, tuple, or dict."""
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, dict):
        if target_field in val and val[target_field] is not None:
            return int(val[target_field])
        if target_field == "supernumerary_seats_allowed" and "supernumerary" in val:
            return int(val["supernumerary"])
    if isinstance(val, (list, tuple)) and len(val) >= 2:
        # convention: (approved_intake, supernumerary_seats_allowed)
        if target_field == "approved_intake":
            return int(val[0])
        elif target_field == "supernumerary_seats_allowed":
            return int(val[1])
    return None


def _match_course_ref(counts: CourseStudentCounts, appr: Any) -> bool:
    """Check if an approved course object matches the CourseStudentCounts."""
    appr_id = getattr(appr, "id", None) if not isinstance(appr, dict) else appr.get("id")
    if counts.course_id is not None and appr_id is not None:
        return str(counts.course_id) == str(appr_id)

    appr_name = getattr(appr, "name", None) if not isinstance(appr, dict) else appr.get("name")
    appr_branch = (
        getattr(appr, "branch", None) if not isinstance(appr, dict) else appr.get("branch")
    )
    if counts.course_name is not None and appr_name is not None:
        name_match = str(counts.course_name).strip().lower() == str(appr_name).strip().lower()
        branch_match = (
            counts.course_branch is None
            or appr_branch is None
            or str(counts.course_branch).strip().lower() == str(appr_branch).strip().lower()
        )
        return name_match and branch_match

    return False


def _find_academic_year(counts: CourseStudentCounts, context: ValidationContext) -> str | None:
    """Find academic year from rows or context."""
    if context.academic_year:
        return context.academic_year
    for row in counts.active_rows:
        yr = context.get_field_value(row, "admission_year")
        if yr:
            return str(yr)
    return None


def _lookup_course_intake_db(
    counts: CourseStudentCounts, academic_year: str, context: ValidationContext
) -> CourseIntake | None:
    """Look up CourseIntake model from database."""
    session = context.db_session
    if session is None:
        return None

    try:
        # If course_id is known
        if counts.course_id is not None:
            return session.scalar(
                select(CourseIntake).where(
                    CourseIntake.course_id == counts.course_id,
                    CourseIntake.academic_year == academic_year,
                )
            )

        # Match via Course joined on name & branch
        if counts.course_name is not None:
            stmt = (
                select(CourseIntake)
                .join(Course, Course.id == CourseIntake.course_id)
                .where(
                    Course.name.ilike(counts.course_name.strip()),
                    CourseIntake.academic_year == academic_year,
                )
            )
            if context.institution_id is not None:
                stmt = stmt.where(Course.institution_id == context.institution_id)
            if counts.course_branch is not None:
                stmt = stmt.where(Course.branch.ilike(counts.course_branch.strip()))
            return session.scalar(stmt)
    except Exception:
        pass

    return None


def _lookup_seat_declaration_db(
    counts: CourseStudentCounts, academic_year: str, context: ValidationContext
) -> SeatDeclaration | None:
    """Look up SeatDeclaration model from database."""
    session = context.db_session
    if session is None:
        return None

    try:
        if counts.course_id is not None:
            return session.scalar(
                select(SeatDeclaration).where(
                    SeatDeclaration.course_id == counts.course_id,
                    SeatDeclaration.academic_year == academic_year,
                )
            )

        if counts.course_name is not None:
            stmt = (
                select(SeatDeclaration)
                .join(Course, Course.id == SeatDeclaration.course_id)
                .where(
                    Course.name.ilike(counts.course_name.strip()),
                    SeatDeclaration.academic_year == academic_year,
                )
            )
            if context.institution_id is not None:
                stmt = stmt.where(Course.institution_id == context.institution_id)
            if counts.course_branch is not None:
                stmt = stmt.where(Course.branch.ilike(counts.course_branch.strip()))
            return session.scalar(stmt)
    except Exception:
        pass

    return None
