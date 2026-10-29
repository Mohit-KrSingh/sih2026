"""Validation rule: SUPERNUMERARY_EXCEEDED."""

from __future__ import annotations

from typing import Any

from app.validation.codes import SUPERNUMERARY_EXCEEDED
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule
from app.validation.rules.course_helpers import (
    get_course_student_counts,
    resolve_approved_supernumerary,
)


@register_rule
class SupernumeraryExceededRule(BaseRule):
    """Flags when supernumerary student admissions exceed AICTE allowed supernumerary quota."""

    code: str = SUPERNUMERARY_EXCEEDED
    scope: ValidationScope = ValidationScope.COURSE
    default_level: ValidationLevel = ValidationLevel.EXCEPTION
    default_params: dict[str, Any] = {}
    description: str = (
        "Supernumerary admitted is above the supernumerary seats AICTE allows. "
        "Message states the exact overshoot."
    )

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        course_groups = get_course_student_counts(context)

        for _group_key, counts in course_groups.items():
            allowed_supernumerary = resolve_approved_supernumerary(counts, context)
            if allowed_supernumerary is None:
                continue

            if counts.supernumerary_count > allowed_supernumerary:
                overshoot = counts.supernumerary_count - allowed_supernumerary
                course_desc = (
                    f" for course '{counts.course_name}'" if counts.course_name else ""
                )
                message = (
                    f"Supernumerary admissions ({counts.supernumerary_count}){course_desc} "
                    f"exceed allowed supernumerary quota ({allowed_supernumerary}) by {overshoot}."
                )
                fix_hint = (
                    "Withdraw excess supernumerary admissions or submit written justification "
                    "with AICTE approval documents."
                )

                row_ref: int | str | None = None
                if counts.course_id is not None:
                    row_ref = counts.course_id
                elif counts.course_name is not None:
                    row_ref = counts.course_name

                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="supernumerary_seats_allowed",
                        message=message,
                        fix_hint=fix_hint,
                        audience=ValidationAudience.BOTH.value,
                        requires_justification=True,
                    )
                )

        return flags


rule = SupernumeraryExceededRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
