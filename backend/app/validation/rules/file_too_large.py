"""Validation rule: FILE_TOO_LARGE."""

from __future__ import annotations

from typing import Any

from app.validation.codes import FILE_TOO_LARGE
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule

DEFAULT_MAX_ROWS: int = 10000


@register_rule
class FileTooLargeRule(BaseRule):
    """Checks that the uploaded file does not exceed the maximum allowed row limit."""

    code: str = FILE_TOO_LARGE
    scope: ValidationScope = ValidationScope.FILE
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {"max_rows": DEFAULT_MAX_ROWS}
    description: str = "Over the row limit (default 10,000). File rejected."

    def check(self, context: ValidationContext) -> list[Flag]:
        max_rows = context.get_param("max_rows", DEFAULT_MAX_ROWS)
        all_rows = context.get_all_rows()
        row_count = context.file_metadata.get("row_count", len(all_rows))

        if row_count > max_rows:
            return [
                Flag(
                    rule_code=self.code,
                    level=self.default_level,
                    field=None,
                    message=(
                        f"Uploaded file contains {row_count:,} rows, which exceeds "
                        f"the maximum limit of {max_rows:,} rows."
                    ),
                    fix_hint=(
                        f"Split your upload into smaller batches containing at most "
                        f"{max_rows:,} student records each."
                    ),
                    audience=ValidationAudience.COLLEGE.value,
                    requires_justification=False,
                )
            ]

        return []


rule = FileTooLargeRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
