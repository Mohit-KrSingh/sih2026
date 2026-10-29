"""Validation rule: NAME_FORMAT."""

from __future__ import annotations

import re
from typing import Any

from app.validation.codes import NAME_FORMAT
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule

# Allowed characters: English letters, spaces, dots, and hyphens
# Must contain only allowed characters AND have at least one letter
NAME_CHARS_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z\s.\-]+$")
HAS_LETTER_PATTERN: re.Pattern[str] = re.compile(r"[A-Za-z]")


@register_rule
class NameFormatRule(BaseRule):
    """Checks that the student name contains only letters, spaces, dots, and hyphens."""

    code: str = NAME_FORMAT
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "Name has digits or illegal characters."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        for idx, row in enumerate(context.get_all_rows(), start=1):
            val = context.get_field_value(row, "name")
            if val is None or str(val).strip() == "":
                # Skip empty values; handled by NAME_REQUIRED
                continue

            val_str = str(val).strip()
            if not NAME_CHARS_PATTERN.match(val_str) or not HAS_LETTER_PATTERN.search(val_str):
                row_ref = context.get_field_value(row, "row_number", idx)
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="name",
                        message=f"Student name '{val_str}' contains digits or illegal characters.",
                        fix_hint=(
                            "Student name must contain only letters, spaces, dots, and hyphens."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )
        return flags


rule = NameFormatRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
