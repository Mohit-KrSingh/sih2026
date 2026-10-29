"""Validation rule: ADMISSION_DATE_WINDOW."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.validation.codes import ADMISSION_DATE_WINDOW
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule

DEFAULT_START_MONTH: int = 5  # May 1
DEFAULT_START_DAY: int = 1
DEFAULT_END_MONTH: int = 11  # November 30
DEFAULT_END_DAY: int = 30


@register_rule
class AdmissionDateWindowRule(BaseRule):
    """Checks that the admission date falls within the designated admission window."""

    code: str = ADMISSION_DATE_WINDOW
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.WARNING
    default_params: dict[str, Any] = {
        "start_month": DEFAULT_START_MONTH,
        "start_day": DEFAULT_START_DAY,
        "end_month": DEFAULT_END_MONTH,
        "end_day": DEFAULT_END_DAY,
    }
    description: str = "Admission date outside the admission window for that year."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []

        start_month = int(context.get_param("start_month", DEFAULT_START_MONTH))
        start_day = int(context.get_param("start_day", DEFAULT_START_DAY))
        end_month = int(context.get_param("end_month", DEFAULT_END_MONTH))
        end_day = int(context.get_param("end_day", DEFAULT_END_DAY))

        for idx, row in enumerate(context.get_all_rows(), start=1):
            adm_val = context.get_field_value(row, "admission_date")
            if adm_val is None or str(adm_val).strip() == "":
                continue

            year_val = context.get_field_value(row, "admission_year") or context.academic_year
            if not year_val:
                continue

            # Extract 4-digit starting calendar year
            year_match = re.search(r"(\d{4})", str(year_val))
            if not year_match:
                continue
            start_year = int(year_match.group(1))

            # Determine window bounds
            window_start_param = context.get_param("window_start")
            window_end_param = context.get_param("window_end")

            try:
                if window_start_param:
                    window_start = (
                        window_start_param
                        if isinstance(window_start_param, date)
                        else date.fromisoformat(str(window_start_param).strip())
                    )
                else:
                    window_start = date(start_year, start_month, start_day)

                if window_end_param:
                    window_end = (
                        window_end_param
                        if isinstance(window_end_param, date)
                        else date.fromisoformat(str(window_end_param).strip())
                    )
                else:
                    window_end = date(start_year, end_month, end_day)
            except (ValueError, TypeError):
                continue

            # Parse admission date
            parsed_date: date | None = None
            if isinstance(adm_val, date) and not isinstance(adm_val, datetime):
                parsed_date = adm_val
            elif isinstance(adm_val, datetime):
                parsed_date = adm_val.date()
            else:
                try:
                    parsed_date = date.fromisoformat(str(adm_val).strip())
                except (ValueError, TypeError):
                    continue

            if parsed_date < window_start or parsed_date > window_end:
                row_ref = context.get_field_value(row, "row_number", idx)
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="admission_date",
                        message=(
                            f"Admission date '{parsed_date.isoformat()}' falls outside the "
                            f"standard admission window ({window_start.isoformat()} to "
                            f"{window_end.isoformat()}) for academic year {year_val}."
                        ),
                        fix_hint=(
                            "Verify that the admission date is correct or provide institutional "
                            "justification for an off-cycle admission."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = AdmissionDateWindowRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
