"""Validation rule: COUNTRY_REQUIRED."""

from __future__ import annotations

from typing import Any

from app.validation.codes import COUNTRY_REQUIRED
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule


@register_rule
class CountryRequiredRule(BaseRule):
    """Checks that country is provided whenever a student is marked as a Foreign National."""

    code: str = COUNTRY_REQUIRED
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "Foreign national is Yes but country is empty."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        for idx, row in enumerate(context.get_all_rows(), start=1):
            fn_val = context.get_field_value(row, "foreign_national")
            if fn_val is not None and str(fn_val).strip().lower() == "yes":
                country_val = context.get_field_value(row, "country")
                if country_val is None or str(country_val).strip() == "":
                    row_ref = context.get_field_value(row, "row_number", idx)
                    flags.append(
                        Flag(
                            rule_code=self.code,
                            level=self.default_level,
                            row_ref=row_ref,
                            field="country",
                            message="Country is required when foreign national status is Yes.",
                            fix_hint=(
                                "Enter the student's country of citizenship "
                                "(for example Nepal, Bhutan, United Arab Emirates)."
                            ),
                            audience=ValidationAudience.COLLEGE.value,
                            requires_justification=False,
                        )
                    )
        return flags


rule = CountryRequiredRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
