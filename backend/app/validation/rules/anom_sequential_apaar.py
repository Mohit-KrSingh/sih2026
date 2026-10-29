"""Validation rule: ANOM_SEQUENTIAL_APAAR."""

from __future__ import annotations

from typing import Any

from app.validation.codes import ANOM_SEQUENTIAL_APAAR
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule
from app.validation.rules.anomaly_helpers import find_longest_sequential_apaar_run
from app.validation.rules.course_helpers import get_course_student_counts


@register_rule
class AnomSequentialApaarRule(BaseRule):
    """Flags when consecutive sequential runs of APAAR IDs exceed threshold."""

    code: str = ANOM_SEQUENTIAL_APAAR
    scope: ValidationScope = ValidationScope.ANOMALY
    default_level: ValidationLevel = ValidationLevel.WARNING
    default_params: dict[str, Any] = {"threshold_run": 10}
    description: str = (
        "Long runs of sequential APAAR IDs (default 10 or more). Audience: aicte"
    )

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        course_groups = get_course_student_counts(context)
        threshold_run = int(context.get_param("threshold_run", 10))

        for _group_key, counts in course_groups.items():
            active_rows = counts.active_rows
            if not active_rows:
                continue

            run_len, start_aid, end_aid = find_longest_sequential_apaar_run(active_rows, context)

            if run_len >= threshold_run and start_aid and end_aid:
                course_desc = (
                    f" in course '{counts.course_name}'" if counts.course_name else ""
                )
                message = (
                    f"Sequential run of {run_len} APAAR IDs detected{course_desc} "
                    f"({start_aid} to {end_aid}), exceeding threshold of {threshold_run}."
                )
                fix_hint = (
                    "Audit registration logs to rule out bulk automated synthetic "
                    "identity submission."
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
                        field="apaar_id",
                        message=message,
                        fix_hint=fix_hint,
                        audience=ValidationAudience.AICTE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = AnomSequentialApaarRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
