"""Validation rule: ANOM_NRI_SHARE."""

from __future__ import annotations

from typing import Any

from app.validation.codes import ANOM_NRI_SHARE
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule
from app.validation.rules.anomaly_helpers import is_international_student
from app.validation.rules.course_helpers import get_course_student_counts


@register_rule
class AnomNriShareRule(BaseRule):
    """Flags when international (NRI, OCI, Foreign National) student share exceeds threshold."""

    code: str = ANOM_NRI_SHARE
    scope: ValidationScope = ValidationScope.ANOMALY
    default_level: ValidationLevel = ValidationLevel.WARNING
    default_params: dict[str, Any] = {"threshold_percent": 25.0}
    description: str = (
        "NRI/OCI/foreign share unusually high (default over 25%). Audience: aicte"
    )

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        course_groups = get_course_student_counts(context)
        threshold_pct = float(context.get_param("threshold_percent", 25.0))

        for _group_key, counts in course_groups.items():
            active_rows = counts.active_rows
            total_students = len(active_rows)
            if total_students <= 0:
                continue

            intl_count = sum(1 for r in active_rows if is_international_student(r, context))
            intl_share_pct = (intl_count / float(total_students)) * 100.0

            if intl_share_pct > threshold_pct:
                course_desc = (
                    f" for course '{counts.course_name}'" if counts.course_name else ""
                )
                message = (
                    f"International student share (NRI/OCI/Foreign National) is "
                    f"{intl_share_pct:.1f}% ({intl_count} of {total_students} students)"
                    f"{course_desc}, exceeding the {threshold_pct:.1f}% threshold."
                )
                fix_hint = (
                    "Audit international quota approvals and candidate citizenship documentation."
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
                        field="nri",
                        message=message,
                        fix_hint=fix_hint,
                        audience=ValidationAudience.AICTE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = AnomNriShareRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
