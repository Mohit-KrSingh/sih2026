"""Validation rule: SEAT_TYPE_NOT_APPROVED."""

from __future__ import annotations

from typing import Any

from app.validation.codes import SEAT_TYPE_NOT_APPROVED
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule


def _is_supernumerary_allowed(row: Any, context: ValidationContext) -> bool | None:
    """Determine whether supernumerary admissions are permitted for the student's course.

    Returns:
        True if supernumerary is permitted.
        False if supernumerary is explicitly disallowed.
        None if course context is not available.
    """
    # 1. Parameter override
    param_allowed = context.get_param("supernumerary_allowed")
    if param_allowed is not None:
        return bool(param_allowed)

    # 2. Direct course on context
    if context.course is not None:
        c = context.course
        if hasattr(c, "supernumerary_allowed"):
            return bool(c.supernumerary_allowed)
        if isinstance(c, dict) and "supernumerary_allowed" in c:
            return bool(c["supernumerary_allowed"])
        if hasattr(c, "supernumerary_seats_allowed"):
            return c.supernumerary_seats_allowed > 0
        if isinstance(c, dict) and "supernumerary_seats_allowed" in c:
            return int(c["supernumerary_seats_allowed"]) > 0

    # 3. Context approved_supernumerary count
    if context.approved_supernumerary is not None:
        return context.approved_supernumerary > 0

    # 4. Extra approved courses
    appr_courses = context.extra.get("approved_courses")
    if not appr_courses:
        db = context.db_session or context.extra.get("db")
        if db is not None and context.institution_id is not None:
            try:
                from sqlalchemy import select

                from app.models import Course
                appr_courses = list(
                    db.scalars(
                        select(Course).where(Course.institution_id == context.institution_id)
                    ).all()
                )
            except Exception:
                pass

    if appr_courses:
        row_course = context.get_field_value(row, "course") or context.get_field_value(
            row, "course_name"
        )
        row_branch = context.get_field_value(row, "branch")
        row_id = context.get_field_value(row, "course_id")

        for appr in appr_courses:
            appr_id = getattr(appr, "id", None) if not isinstance(appr, dict) else appr.get("id")
            appr_name = (
                getattr(appr, "name", None) if not isinstance(appr, dict) else appr.get("name")
            )
            appr_branch = (
                getattr(appr, "branch", None) if not isinstance(appr, dict) else appr.get("branch")
            )

            id_match = row_id is not None and appr_id is not None and str(row_id) == str(appr_id)
            name_match = (
                row_course is not None
                and appr_name is not None
                and str(row_course).strip().lower() == str(appr_name).strip().lower()
                and (
                    row_branch is None
                    or appr_branch is None
                    or str(row_branch).strip().lower() == str(appr_branch).strip().lower()
                )
            )

            if id_match or name_match:
                if hasattr(appr, "supernumerary_allowed"):
                    return bool(appr.supernumerary_allowed)
                if isinstance(appr, dict) and "supernumerary_allowed" in appr:
                    return bool(appr["supernumerary_allowed"])
                if hasattr(appr, "supernumerary_seats_allowed"):
                    return appr.supernumerary_seats_allowed > 0
                if isinstance(appr, dict) and "supernumerary_seats_allowed" in appr:
                    return int(appr["supernumerary_seats_allowed"]) > 0
                return False

    # 5. Direct row metadata
    row_super = context.get_field_value(row, "supernumerary_allowed")
    if row_super is not None:
        return bool(row_super)

    return None


@register_rule
class SeatTypeNotApprovedRule(BaseRule):
    """Checks that supernumerary seats are only claimed for courses where AICTE permits them."""

    code: str = SEAT_TYPE_NOT_APPROVED
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "Supernumerary seat in a course with no supernumerary seats allowed."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []

        for idx, row in enumerate(context.get_all_rows(), start=1):
            seat_type = context.get_field_value(row, "seat_type")
            if seat_type is None or str(seat_type).strip().lower() != "supernumerary":
                continue

            allowed = _is_supernumerary_allowed(row, context)
            if allowed is False:
                row_ref = context.get_field_value(row, "row_number", idx)
                course_name = (
                    context.get_field_value(row, "course")
                    or context.get_field_value(row, "course_name")
                    or getattr(context.course, "name", None)
                    or "the selected course"
                )
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="seat_type",
                        message=(
                            f"Supernumerary seat type is not approved for course '{course_name}'."
                        ),
                        fix_hint=(
                            "Change seat type to 'Regular' or verify AICTE course "
                            "supernumerary approval."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = SeatTypeNotApprovedRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
