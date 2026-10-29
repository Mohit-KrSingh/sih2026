"""Validation rule: CATEGORY_CONFLICT."""

from __future__ import annotations

from typing import Any

from app.validation.codes import CATEGORY_CONFLICT
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule


@register_rule
class CategoryConflictRule(BaseRule):
    """Checks that a student is not simultaneously marked as both an NRI and a Foreign National."""

    code: str = CATEGORY_CONFLICT
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "NRI and foreign national both Yes."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        for idx, row in enumerate(context.get_all_rows(), start=1):
            nri_val = context.get_field_value(row, "nri")
            fn_val = context.get_field_value(row, "foreign_national")

            is_nri = nri_val is not None and str(nri_val).strip().lower() == "yes"
            is_fn = fn_val is not None and str(fn_val).strip().lower() == "yes"

            if is_nri and is_fn:
                row_ref = context.get_field_value(row, "row_number", idx)
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="nri",
                        message=(
                            "Student cannot be simultaneously marked as both "
                            "an NRI and a Foreign National."
                        ),
                        fix_hint=(
                            "Update either 'nri' or 'foreign_national' to 'No' "
                            "according to the student's legal citizenship status."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = CategoryConflictRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
