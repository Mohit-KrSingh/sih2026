"""Validation rule: DOB_INVALID."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.validation.codes import DOB_INVALID
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule

DOB_ISO_PATTERN: re.Pattern[str] = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@register_rule
class DobInvalidRule(BaseRule):
    """Checks that date of birth is a valid ISO date (YYYY-MM-DD) and not in the future."""

    code: str = DOB_INVALID
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "Not a valid date, or in the future."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        today = date.today()

        for idx, row in enumerate(context.get_all_rows(), start=1):
            val = context.get_field_value(row, "dob")
            row_ref = context.get_field_value(row, "row_number", idx)

            if val is None or str(val).strip() == "":
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="dob",
                        message="Date of birth is missing.",
                        fix_hint="Enter a valid date of birth in YYYY-MM-DD format.",
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )
                continue

            parsed_date: date | None = None
            if isinstance(val, date) and not isinstance(val, datetime):
                parsed_date = val
            elif isinstance(val, datetime):
                parsed_date = val.date()
            else:
                val_str = str(val).strip()
                if not DOB_ISO_PATTERN.match(val_str):
                    flags.append(
                        Flag(
                            rule_code=self.code,
                            level=self.default_level,
                            row_ref=row_ref,
                            field="dob",
                            message=(
                                f"Date of birth '{val_str}' is not in valid "
                                "ISO format (YYYY-MM-DD)."
                            ),
                            fix_hint=(
                                "Enter date of birth in YYYY-MM-DD format (for example 2004-05-10)."
                            ),
                            audience=ValidationAudience.COLLEGE.value,
                            requires_justification=False,
                        )
                    )
                    continue

                try:
                    parsed_date = date.fromisoformat(val_str)
                except (ValueError, TypeError):
                    flags.append(
                        Flag(
                            rule_code=self.code,
                            level=self.default_level,
                            row_ref=row_ref,
                            field="dob",
                            message=f"Date of birth '{val_str}' is not a valid calendar date.",
                            fix_hint="Enter a valid calendar date in YYYY-MM-DD format.",
                            audience=ValidationAudience.COLLEGE.value,
                            requires_justification=False,
                        )
                    )
                    continue

            if parsed_date > today:
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="dob",
                        message=f"Date of birth '{parsed_date.isoformat()}' is in the future.",
                        fix_hint="Enter the student's actual past date of birth.",
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )
            elif parsed_date.year < 1900:
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="dob",
                        message=(
                            f"Date of birth '{parsed_date.isoformat()}' is invalid "
                            "(year must be 1900 or later)."
                        ),
                        fix_hint="Enter a valid date of birth with a 4-digit year 1900 or later.",
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = DobInvalidRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
