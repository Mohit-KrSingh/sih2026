"""Validation rule: DUP_ENROLNO_IN_COURSE."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models import Student
from app.validation.codes import DUP_ENROLNO_IN_COURSE
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule


def _extract_course_keys(
    context: ValidationContext, item: Any
) -> tuple[str, str]:
    """Extract (comparison_key, display_name) for a course from row or student object."""
    course_id = context.get_field_value(item, "course_id")
    course_raw = context.get_field_value(item, "course")
    branch_raw = context.get_field_value(item, "branch")

    course_name = ""
    if course_raw is not None:
        if hasattr(course_raw, "name"):
            course_name = str(course_raw.name).strip()
        else:
            course_name = str(course_raw).strip()

    branch_name = ""
    if branch_raw is not None:
        branch_name = str(branch_raw).strip()

    if course_id is not None:
        key = f"id:{course_id}"
        display = course_name or f"Course #{course_id}"
    else:
        norm_c = course_name.lower().replace("&", "and")
        norm_b = branch_name.lower()
        key = f"name:{norm_c}:{norm_b}"
        display = course_name or "Unknown Course"
        if branch_name:
            display = f"{course_name} ({branch_name})"

    return key, display


@register_rule
class DupEnrolnoInCourseRule(BaseRule):
    """Flags duplicate student enrolment numbers within the same course and academic year."""

    code: str = DUP_ENROLNO_IN_COURSE
    scope: ValidationScope = ValidationScope.FILE
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "Same enrolment number twice in one course and year."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        rows = context.get_all_rows()
        if not rows:
            return flags

        # 1. Group rows by (enrolment_no_lower, course_key, academic_year)
        enrol_map: dict[tuple[str, str, str], list[dict[str, Any]]] = {}

        for idx, row in enumerate(rows, start=1):
            enrol_raw = context.get_field_value(row, "enrolment_no")
            if enrol_raw is None:
                continue
            enrol_str = str(enrol_raw).strip()
            if not enrol_str:
                continue

            course_key, course_display = _extract_course_keys(context, row)
            year_raw = context.get_field_value(
                row, "admission_year", context.academic_year or ""
            )
            year_str = str(year_raw or "").strip()

            row_ref = context.get_field_value(row, "row_number", idx)
            student_id = context.get_field_value(
                row, "id", context.get_field_value(row, "student_id")
            )

            group_key = (enrol_str.lower(), course_key, year_str)
            enrol_map.setdefault(group_key, []).append(
                {
                    "idx": idx,
                    "row": row,
                    "row_ref": row_ref,
                    "student_id": student_id,
                    "enrolment_no": enrol_str,
                    "course_key": course_key,
                    "course_display": course_display,
                    "academic_year": year_str,
                }
            )

        # 2. Check for duplicates within the current upload
        flagged_batch_refs: set[Any] = set()
        for (_, _, _), items in enrol_map.items():
            if len(items) > 1:
                row_refs_str = ", ".join(str(it["row_ref"]) for it in items)
                for it in items:
                    flags.append(
                        Flag(
                            rule_code=self.code,
                            level=self.default_level,
                            row_ref=it["row_ref"],
                            field="enrolment_no",
                            message=(
                                f"Enrolment number '{it['enrolment_no']}' appears multiple times "
                                f"for course '{it['course_display']}' in academic year "
                                f"{it['academic_year']} (rows {row_refs_str})."
                            ),
                            fix_hint=(
                                "Ensure each student has a unique college enrolment "
                                "number within the course."
                            ),
                            audience=ValidationAudience.COLLEGE.value,
                            requires_justification=False,
                        )
                    )
                    flagged_batch_refs.add(it["row_ref"])

        # 3. Check against existing college records for that course and academic year
        inst_id = context.institution_id

        if inst_id is not None:
            # 3a. Check in-memory all_college_students if provided
            if context.all_college_students:
                for existing in context.all_college_students:
                    ex_enrol_raw = context.get_field_value(existing, "enrolment_no")
                    if ex_enrol_raw is None:
                        continue
                    ex_enrol_str = str(ex_enrol_raw).strip()
                    if not ex_enrol_str:
                        continue

                    ex_status = context.get_field_value(existing, "status")
                    if ex_status in ("withdrawn", "transferred"):
                        continue

                    ex_inst = context.get_field_value(existing, "institution_id")
                    if ex_inst is not None and ex_inst != inst_id:
                        continue

                    ex_course_key, _ = _extract_course_keys(context, existing)
                    ex_year_raw = context.get_field_value(existing, "academic_year")
                    ex_year_str = str(ex_year_raw or "").strip()

                    lookup_key = (ex_enrol_str.lower(), ex_course_key, ex_year_str)
                    matching_items = enrol_map.get(lookup_key, [])
                    if not matching_items:
                        continue

                    ex_id = context.get_field_value(
                        existing, "id", context.get_field_value(existing, "student_id")
                    )

                    for it in matching_items:
                        if it["row_ref"] in flagged_batch_refs:
                            continue
                        if (
                            ex_id is not None
                            and it["student_id"] is not None
                            and str(ex_id) == str(it["student_id"])
                        ):
                            continue

                        flags.append(
                            Flag(
                                rule_code=self.code,
                                level=self.default_level,
                                row_ref=it["row_ref"],
                                field="enrolment_no",
                                message=(
                                    f"Enrolment number '{it['enrolment_no']}' already exists "
                                    f"in college records for course '{it['course_display']}' "
                                    f"in academic year {it['academic_year']}."
                                ),
                                fix_hint=(
                                    "Verify enrolment number with institutional records "
                                    "and assign a unique identifier."
                                ),
                                audience=ValidationAudience.COLLEGE.value,
                                requires_justification=False,
                            )
                        )
                        flagged_batch_refs.add(it["row_ref"])

            # 3b. Query database if db_session is provided
            elif context.db_session is not None:
                distinct_enrols = list({k[0] for k in enrol_map.keys()})
                if distinct_enrols:
                    query = (
                        select(Student)
                        .options(joinedload(Student.course))
                        .where(
                            Student.institution_id == inst_id,
                            Student.enrolment_no.in_(
                                [it["enrolment_no"] for items in enrol_map.values() for it in items]
                            ),
                            Student.status.not_in(["withdrawn", "transferred"]),
                        )
                    )
                    if context.academic_year:
                        query = query.where(Student.academic_year == str(context.academic_year))

                    db_students = context.db_session.scalars(query).all()
                    for ex_student in db_students:
                        ex_course_key, _ = _extract_course_keys(context, ex_student)
                        ex_year = ex_student.academic_year or ""
                        ex_key = (ex_student.enrolment_no.lower(), ex_course_key, ex_year)

                        matching_items = enrol_map.get(ex_key, [])
                        for it in matching_items:
                            if it["row_ref"] in flagged_batch_refs:
                                continue
                            if it["student_id"] is not None and str(ex_student.id) == str(
                                it["student_id"]
                            ):
                                continue

                            flags.append(
                                Flag(
                                    rule_code=self.code,
                                    level=self.default_level,
                                    row_ref=it["row_ref"],
                                    field="enrolment_no",
                                    message=(
                                        f"Enrolment number '{it['enrolment_no']}' already exists "
                                        f"in college records for course '{it['course_display']}' "
                                        f"in academic year {it['academic_year']}."
                                    ),
                                    fix_hint=(
                                        "Verify enrolment number with institutional records "
                                        "and assign a unique identifier."
                                    ),
                                    audience=ValidationAudience.COLLEGE.value,
                                    requires_justification=False,
                                )
                            )
                            flagged_batch_refs.add(it["row_ref"])

        return flags


rule = DupEnrolnoInCourseRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
