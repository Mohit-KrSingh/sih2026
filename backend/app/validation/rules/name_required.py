"""Validation rule: NAME_REQUIRED."""

from __future__ import annotations

from typing import Any

from app.validation.codes import NAME_REQUIRED
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule


@register_rule
class NameRequiredRule(BaseRule):
    """Checks that the student name field is present and non-empty."""

    code: str = NAME_REQUIRED
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "Name missing."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        for idx, row in enumerate(context.get_all_rows(), start=1):
            val = context.get_field_value(row, "name")
            if val is None or str(val).strip() == "":
                row_ref = context.get_field_value(row, "row_number", idx)
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="name",
                        message="Student name is missing.",
                        fix_hint="Enter the student's full legal name as per official records.",
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )
        return flags


rule = NameRequiredRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
