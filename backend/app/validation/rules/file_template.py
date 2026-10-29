"""Validation rule: FILE_TEMPLATE."""

from __future__ import annotations

from typing import Any

from app.validation.codes import FILE_TEMPLATE
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule

EXPECTED_COLUMNS: list[str] = [
    "apaar_id",
    "name",
    "dob",
    "gender",
    "course",
    "branch",
    "admission_year",
    "enrolment_no",
    "admission_date",
    "admission_mode",
    "seat_type",
    "reservation_category",
    "nri",
    "oci",
    "foreign_national",
    "country",
]


@register_rule
class FileTemplateRule(BaseRule):
    """Checks that the file contains all required columns in lowercase."""

    code: str = FILE_TEMPLATE
    scope: ValidationScope = ValidationScope.FILE
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {"expected_columns": EXPECTED_COLUMNS}
    description: str = "Wrong or missing columns. File rejected, nothing saved."

    def check(self, context: ValidationContext) -> list[Flag]:
        expected = context.get_param("expected_columns", EXPECTED_COLUMNS)
        # Extract headers from file_metadata, or from dict row keys if file_metadata empty
        headers = context.file_metadata.get("headers")
        if headers is None and context.rows:
            first_row = context.rows[0]
            if isinstance(first_row, dict):
                headers = list(first_row.keys())

        if headers is None:
            return []

        normalized_headers = [str(h).strip().lower() for h in headers]
        missing = [col for col in expected if col not in normalized_headers]

        if missing:
            return [
                Flag(
                    rule_code=self.code,
                    level=self.default_level,
                    field="headers",
                    message=(
                        "Uploaded file template is invalid. Missing required column(s): "
                        f"{', '.join(missing)}."
                    ),
                    fix_hint=(
                        "Download the standard CSV template and ensure all 16 required columns "
                        "are present in lowercase."
                    ),
                    audience=ValidationAudience.COLLEGE.value,
                    requires_justification=False,
                )
            ]

        return []


rule = FileTemplateRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
