"""Validation rule: APAAR_DOB_MISMATCH."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.validation.apaar_lookup import get_apaar_cache
from app.validation.codes import APAAR_DOB_MISMATCH
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule

APAAR_REGEX = re.compile(r"^\d{12}$")


def _parse_date(val: Any) -> date | None:
    """Safely parse value into a datetime.date object."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        try:
            return date.fromisoformat(val_str)
        except (ValueError, TypeError):
            return None
    return None


@register_rule
class ApaarDobMismatchRule(BaseRule):
    """Checks that the student's date of birth matches the APAAR registry record."""

    code: str = APAAR_DOB_MISMATCH
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "Date of birth differs from the registry."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        cache = get_apaar_cache(context)

        for idx, row in enumerate(context.get_all_rows(), start=1):
            val = context.get_field_value(row, "apaar_id")
            if val is None:
                continue
            aid = str(val).strip()
            # Cheap check first: skip format-invalid rows
            if not APAAR_REGEX.match(aid):
                continue

            record = cache.get(aid)
            # If record not found, APAAR_NOT_FOUND handles it
            if record is None:
                continue

            dob_val = context.get_field_value(row, "dob")
            row_dob = _parse_date(dob_val)
            # Skip invalid or missing DOB formats (handled by DOB_INVALID)
            if row_dob is None:
                continue

            reg_dob = _parse_date(record.dob)
            if reg_dob is None:
                continue

            if row_dob != reg_dob:
                row_ref = context.get_field_value(row, "row_number", idx)
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="dob",
                        message=(
                            f"Student date of birth '{row_dob.isoformat()}' does not match "
                            f"APAAR registry date of birth '{reg_dob.isoformat()}'."
                        ),
                        fix_hint=(
                            "Update the date of birth to match the student's official "
                            f"APAAR registry record ({reg_dob.isoformat()})."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = ApaarDobMismatchRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
