"""Validation rule: FILE_EMPTY."""

from __future__ import annotations

from typing import Any

from app.validation.codes import FILE_EMPTY
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule


@register_rule
class FileEmptyRule(BaseRule):
    """Checks that the file contains at least one student data row."""

    code: str = FILE_EMPTY
    scope: ValidationScope = ValidationScope.FILE
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "No data rows. File rejected."

    def check(self, context: ValidationContext) -> list[Flag]:
        all_rows = context.get_all_rows()
        row_count = context.file_metadata.get("row_count")

        # Check if rows list is empty or row_count is explicitly 0
        if (row_count is not None and row_count == 0) or len(all_rows) == 0:
            return [
                Flag(
                    rule_code=self.code,
                    level=self.default_level,
                    field=None,
                    message="Uploaded file contains no student data rows.",
                    fix_hint="Add at least one student record below the header row and re-upload.",
                    audience=ValidationAudience.COLLEGE.value,
                    requires_justification=False,
                )
            ]

        return []


rule = FileEmptyRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
