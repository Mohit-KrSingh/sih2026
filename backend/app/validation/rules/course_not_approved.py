"""Validation rule: COURSE_NOT_APPROVED."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models import Course
from app.validation.codes import COURSE_NOT_APPROVED
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule


def _get_approved_courses(context: ValidationContext) -> list[Any] | None:
    """Retrieve approved course list from context sources or None if not configured."""
    if "approved_courses" in context.extra:
        val = context.extra["approved_courses"]
        return list(val.values()) if isinstance(val, dict) else list(val)
    if context.get_param("approved_courses") is not None:
        val = context.get_param("approved_courses")
        return list(val.values()) if isinstance(val, dict) else list(val)
    if context.course is not None:
        return [context.course]
    if context.aicte_client is not None:
        aicte_id = context.extra.get("aicte_id")
        if aicte_id:
            try:
                courses = context.aicte_client.get_courses(aicte_id)
                if courses:
                    return list(courses)
            except Exception:
                pass
    db = context.db_session or context.extra.get("db")
    if db is not None and context.institution_id is not None:
        try:
            return list(
                db.scalars(
                    select(Course).where(Course.institution_id == context.institution_id)
                ).all()
            )
        except Exception:
            pass
    return None


def _course_matches(row_course: str | None, row_branch: str | None, row_id: Any, appr: Any) -> bool:
    """Check if a row's course identifiers match an approved course object or dict."""
    appr_id = getattr(appr, "id", None) if not isinstance(appr, dict) else appr.get("id")
    if row_id is not None and appr_id is not None and str(row_id) == str(appr_id):
        return True

    appr_name = getattr(appr, "name", None) if not isinstance(appr, dict) else appr.get("name")
    appr_branch = (
        getattr(appr, "branch", None) if not isinstance(appr, dict) else appr.get("branch")
    )

    if row_course is not None and appr_name is not None:
        name_match = str(row_course).strip().lower() == str(appr_name).strip().lower()
        if not name_match:
            return False

        if row_branch is not None and appr_branch is not None:
            return str(row_branch).strip().lower() == str(appr_branch).strip().lower()
        if row_branch is None and appr_branch is None:
            return True

    return False


@register_rule
class CourseNotApprovedRule(BaseRule):
    """Checks that a student's course and branch are in the institution's approved list."""

    code: str = COURSE_NOT_APPROVED
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "Course or branch not approved for this college."

    def check(self, context: ValidationContext) -> list[Flag]:
        approved_courses = _get_approved_courses(context)
        if approved_courses is None:
            # Course context not provided; skip check without raising false positives
            return []

        flags: list[Flag] = []
        for idx, row in enumerate(context.get_all_rows(), start=1):
            row_course = context.get_field_value(row, "course") or context.get_field_value(
                row, "course_name"
            )
            row_branch = context.get_field_value(row, "branch")
            row_course_id = context.get_field_value(row, "course_id")

            # Skip format-empty values handled by cheap-check rules
            if row_course is None and row_branch is None and row_course_id is None:
                continue

            matched = any(
                _course_matches(row_course, row_branch, row_course_id, appr)
                for appr in approved_courses
            )

            if not matched:
                row_ref = context.get_field_value(row, "row_number", idx)
                course_display = row_course or f"ID {row_course_id}"
                branch_info = f" (branch '{row_branch}')" if row_branch else ""
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="course",
                        message=(
                            f"Course '{course_display}'{branch_info} is not approved "
                            "for this institution."
                        ),
                        fix_hint=(
                            "Select an approved course and branch from the institution's "
                            "approved AICTE curriculum list."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = CourseNotApprovedRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
