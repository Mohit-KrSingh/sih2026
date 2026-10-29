"""Validation rule: ANOM_DOB_CLUSTER."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.validation.codes import ANOM_DOB_CLUSTER
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule
from app.validation.rules.anomaly_helpers import get_row_dob
from app.validation.rules.course_helpers import get_course_student_counts


@register_rule
class AnomDobClusterRule(BaseRule):
    """Flags when multiple students in a course share the exact date of birth."""

    code: str = ANOM_DOB_CLUSTER
    scope: ValidationScope = ValidationScope.ANOMALY
    default_level: ValidationLevel = ValidationLevel.WARNING
    default_params: dict[str, Any] = {"threshold_count": 5}
    description: str = (
        "Many students share one date of birth (default 5 or more). Audience: aicte"
    )

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        course_groups = get_course_student_counts(context)
        threshold_count = int(context.get_param("threshold_count", 5))

        for _group_key, counts in course_groups.items():
            active_rows = counts.active_rows
            if not active_rows:
                continue

            dob_counter: Counter[str] = Counter()
            for r in active_rows:
                dob = get_row_dob(r, context)
                if dob:
                    dob_counter[dob] += 1

            for dob_str, cluster_count in dob_counter.most_common():
                if cluster_count >= threshold_count:
                    course_desc = (
                        f" in course '{counts.course_name}'" if counts.course_name else ""
                    )
                    message = (
                        f"Cluster of {cluster_count} students{course_desc} sharing the exact "
                        f"date of birth {dob_str} (threshold: {threshold_count})."
                    )
                    fix_hint = "Verify identity documentation for date of birth records."

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
                            field="dob",
                            message=message,
                            fix_hint=fix_hint,
                            audience=ValidationAudience.AICTE.value,
                            requires_justification=False,
                        )
                    )

        return flags


rule = AnomDobClusterRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
