"""Validation rule: ADMISSION_YEAR_MISMATCH."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.validation.codes import ADMISSION_YEAR_MISMATCH
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule

DEFAULT_ACAD_START_MONTH: int = 4  # April 1
DEFAULT_ACAD_START_DAY: int = 1
DEFAULT_ACAD_END_MONTH: int = 6  # June 30 of following year
DEFAULT_ACAD_END_DAY: int = 30


def _parse_date(val: Any) -> date | None:
    """Parse date from date, datetime, or ISO string."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        return date.fromisoformat(str(val).strip())
    except (ValueError, TypeError):
        return None


@register_rule
class AdmissionYearMismatchRule(BaseRule):
    """Checks that the admission date falls within the calendar span of the stated academic year."""

    code: str = ADMISSION_YEAR_MISMATCH
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.WARNING
    default_params: dict[str, Any] = {
        "start_month": DEFAULT_ACAD_START_MONTH,
        "start_day": DEFAULT_ACAD_START_DAY,
        "end_month": DEFAULT_ACAD_END_MONTH,
        "end_day": DEFAULT_ACAD_END_DAY,
    }
    description: str = "Admission date does not fall in the stated academic year."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []

        start_month = int(context.get_param("start_month", DEFAULT_ACAD_START_MONTH))
        start_day = int(context.get_param("start_day", DEFAULT_ACAD_START_DAY))
        end_month = int(context.get_param("end_month", DEFAULT_ACAD_END_MONTH))
        end_day = int(context.get_param("end_day", DEFAULT_ACAD_END_DAY))

        for idx, row in enumerate(context.get_all_rows(), start=1):
            adm_raw = context.get_field_value(row, "admission_date")
            adm_date = _parse_date(adm_raw)
            if adm_date is None:
                # Cheap checks handle missing or format-invalid dates
                continue

            year_val = (
                context.get_field_value(row, "admission_year") or context.academic_year
            )
            if not year_val:
                continue

            m = re.search(r"(\d{4})(?:-(\d{2,4}))?", str(year_val).strip())
            if not m:
                continue

            start_year = int(m.group(1))
            end_group = m.group(2)
            if end_group:
                if len(end_group) == 2:
                    end_year = (start_year // 100) * 100 + int(end_group)
                else:
                    end_year = int(end_group)
            else:
                end_year = start_year + 1

            try:
                bound_start = date(start_year, start_month, start_day)
                bound_end = date(end_year, end_month, end_day)
            except (ValueError, TypeError):
                continue

            if adm_date < bound_start or adm_date > bound_end:
                row_ref = context.get_field_value(row, "row_number", idx)
                requires_justification = bool(context.get_param("requires_justification", False))
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="admission_date",
                        message=(
                            f"Admission date '{adm_date.isoformat()}' does not fall within "
                            f"academic year {year_val} ({bound_start.isoformat()} to "
                            f"{bound_end.isoformat()})."
                        ),
                        fix_hint=(
                            f"Verify admission date or update admission year to match "
                            f"the actual enrolment cycle ({year_val})."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=requires_justification,
                    )
                )

        return flags


rule = AdmissionYearMismatchRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
