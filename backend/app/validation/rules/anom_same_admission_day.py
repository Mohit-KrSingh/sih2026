"""Validation rule: ANOM_SAME_ADMISSION_DAY."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.validation.codes import ANOM_SAME_ADMISSION_DAY
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule
from app.validation.rules.anomaly_helpers import get_row_admission_date
from app.validation.rules.course_helpers import get_course_student_counts


@register_rule
class AnomSameAdmissionDayRule(BaseRule):
    """Flags when a large share of admissions occur on a single calendar day."""

    code: str = ANOM_SAME_ADMISSION_DAY
    scope: ValidationScope = ValidationScope.ANOMALY
    default_level: ValidationLevel = ValidationLevel.INFO
    default_params: dict[str, Any] = {"threshold_percent": 60.0, "min_students": 5}
    description: str = (
        "Large share of students admitted on one day (default over 60%). Audience: aicte"
    )

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        course_groups = get_course_student_counts(context)
        threshold_pct = float(context.get_param("threshold_percent", 60.0))
        min_students = int(context.get_param("min_students", 5))

        for _group_key, counts in course_groups.items():
            active_rows = counts.active_rows
            total_students = len(active_rows)
            if total_students < min_students:
                continue

            date_counter: Counter[str] = Counter()
            for r in active_rows:
                adm_date = get_row_admission_date(r, context)
                if adm_date:
                    date_counter[adm_date] += 1

            if not date_counter:
                continue

            top_date, max_count = date_counter.most_common(1)[0]
            concentration_pct = (max_count / float(total_students)) * 100.0

            if concentration_pct >= threshold_pct:
                course_desc = (
                    f" for course '{counts.course_name}'" if counts.course_name else ""
                )
                message = (
                    f"{concentration_pct:.1f}% of students ({max_count} of {total_students}) "
                    f"admitted on a single date ({top_date}){course_desc}, "
                    f"exceeding the {threshold_pct:.1f}% threshold."
                )
                fix_hint = (
                    "Confirm batch counseling round or institutional single-window admission drive."
                )

                row_ref: int | str | None = None
                if counts.course_id is not None:
                    row_ref = counts.course_id
                elif counts.course_name is not None:
                    row_ref = counts.course_name

                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="admission_date",
                        message=message,
                        fix_hint=fix_hint,
                        audience=ValidationAudience.AICTE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = AnomSameAdmissionDayRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
