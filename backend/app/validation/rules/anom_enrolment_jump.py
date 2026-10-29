"""Validation rule: ANOM_ENROLMENT_JUMP."""

from __future__ import annotations

from typing import Any

from app.validation.codes import ANOM_ENROLMENT_JUMP
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule
from app.validation.rules.anomaly_helpers import resolve_previous_year_enrolment
from app.validation.rules.course_helpers import get_course_student_counts


@register_rule
class AnomEnrolmentJumpRule(BaseRule):
    """Flags when college-course enrolment jumps more than configured threshold over prior year."""

    code: str = ANOM_ENROLMENT_JUMP
    scope: ValidationScope = ValidationScope.ANOMALY
    default_level: ValidationLevel = ValidationLevel.WARNING
    default_params: dict[str, Any] = {"threshold_percent": 30.0}
    description: str = (
        "Enrolment up more than a threshold (default 30%) against last year. Audience: aicte"
    )

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        course_groups = get_course_student_counts(context)
        threshold_pct = float(context.get_param("threshold_percent", 30.0))

        for _group_key, counts in course_groups.items():
            current_count = len(counts.active_rows)
            prev_count = resolve_previous_year_enrolment(counts, context)

            if prev_count is None or prev_count <= 0:
                continue

            pct_jump = ((current_count - prev_count) / float(prev_count)) * 100.0

            if pct_jump > threshold_pct:
                course_desc = (
                    f" for course '{counts.course_name}'" if counts.course_name else ""
                )
                academic_year = context.academic_year or "current year"
                prev_year_str = "previous year"
                if context.academic_year and "-" in context.academic_year:
                    parts = context.academic_year.split("-")
                    try:
                        start_y = int(parts[0])
                        prev_year_str = f"{start_y - 1}-{(start_y) % 100:02d}"
                    except Exception:
                        pass

                message = (
                    f"Enrolment jumped from {prev_count} in {prev_year_str} to {current_count} "
                    f"in {academic_year} (+{pct_jump:.1f}%){course_desc}, "
                    f"exceeding the {threshold_pct:.1f}% threshold."
                )
                fix_hint = "Verify admission register and council approval for intake scaling."

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
                        field="enrolment_total",
                        message=message,
                        fix_hint=fix_hint,
                        audience=ValidationAudience.AICTE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = AnomEnrolmentJumpRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
