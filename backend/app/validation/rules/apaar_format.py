"""Validation rule: APAAR_FORMAT."""

from __future__ import annotations

import re
from typing import Any

from app.validation.codes import APAAR_FORMAT
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule

APAAR_PATTERN: re.Pattern[str] = re.compile(r"^\d{12}$")


@register_rule
class ApaarFormatRule(BaseRule):
    """Checks that the APAAR ID consists of exactly 12 numeric digits."""

    code: str = APAAR_FORMAT
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "Not exactly 12 digits."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        for idx, row in enumerate(context.get_all_rows(), start=1):
            val = context.get_field_value(row, "apaar_id")
            if val is None or str(val).strip() == "":
                # Skip empty values; handled by APAAR_REQUIRED
                continue

            val_str = str(val).strip()
            if not APAAR_PATTERN.match(val_str):
                row_ref = context.get_field_value(row, "row_number", idx)
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="apaar_id",
                        message=(
                            f"APAAR ID '{val_str}' is invalid. "
                            "It must be exactly 12 numeric digits."
                        ),
                        fix_hint=(
                            "Enter a 12-digit numeric APAAR ID without letters, spaces, or hyphens."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )
        return flags


rule = ApaarFormatRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
