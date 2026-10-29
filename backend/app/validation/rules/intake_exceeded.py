"""Validation rule: INTAKE_EXCEEDED."""

from __future__ import annotations

from typing import Any

from app.validation.codes import INTAKE_EXCEEDED
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule
from app.validation.rules.course_helpers import (
    get_course_student_counts,
    resolve_approved_intake,
)


@register_rule
class IntakeExceededRule(BaseRule):
    """Flags when regular student admissions exceed AICTE approved intake for a course."""

    code: str = INTAKE_EXCEEDED
    scope: ValidationScope = ValidationScope.COURSE
    default_level: ValidationLevel = ValidationLevel.EXCEPTION
    default_params: dict[str, Any] = {}
    description: str = (
        "Regular admitted is above approved intake. Message states the exact overshoot."
    )

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        course_groups = get_course_student_counts(context)

        for _group_key, counts in course_groups.items():
            approved_intake = resolve_approved_intake(counts, context)
            if approved_intake is None:
                continue

            if counts.regular_count > approved_intake:
                overshoot = counts.regular_count - approved_intake
                course_desc = (
                    f" for course '{counts.course_name}'" if counts.course_name else ""
                )
                message = (
                    f"Regular admissions ({counts.regular_count}){course_desc} "
                    f"exceed approved intake ({approved_intake}) by {overshoot}."
                )
                fix_hint = (
                    "Withdraw excess regular admissions, reclassify valid supernumerary "
                    "candidates, or submit written justification with official approval "
                    "documentation."
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
                        field="approved_intake",
                        message=message,
                        fix_hint=fix_hint,
                        audience=ValidationAudience.BOTH.value,
                        requires_justification=True,
                    )
                )

        return flags


rule = IntakeExceededRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
