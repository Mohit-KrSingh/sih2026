"""Validation rule: APAAR_REQUIRED."""

from __future__ import annotations

from typing import Any

from app.validation.codes import APAAR_REQUIRED
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule


@register_rule
class ApaarRequiredRule(BaseRule):
    """Checks that the APAAR ID field is present and non-empty for every student row."""

    code: str = APAAR_REQUIRED
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "APAAR ID missing."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        for idx, row in enumerate(context.get_all_rows(), start=1):
            val = context.get_field_value(row, "apaar_id")
            if val is None or str(val).strip() == "":
                row_ref = context.get_field_value(row, "row_number", idx)
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="apaar_id",
                        message="APAAR ID is missing.",
                        fix_hint="Enter the student's 12-digit APAAR ID.",
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )
        return flags


rule = ApaarRequiredRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
