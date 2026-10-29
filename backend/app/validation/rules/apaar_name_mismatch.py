"""Validation rule: APAAR_NAME_MISMATCH."""

from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz, utils

from app.validation.apaar_lookup import get_apaar_cache
from app.validation.codes import APAAR_NAME_MISMATCH
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule

APAAR_REGEX = re.compile(r"^\d{12}$")
DEFAULT_THRESHOLD: float = 85.0


@register_rule
class ApaarNameMismatchRule(BaseRule):
    """Checks that the student's name matches the APAAR registry record within a fuzzy threshold."""

    code: str = APAAR_NAME_MISMATCH
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.WARNING
    default_params: dict[str, Any] = {"threshold": 85}
    description: str = "Fuzzy name match below threshold (default 85)."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        cache = get_apaar_cache(context)

        threshold_val = context.get_param("threshold", DEFAULT_THRESHOLD)
        try:
            threshold = float(threshold_val)
        except (ValueError, TypeError):
            threshold = DEFAULT_THRESHOLD

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

            name_val = context.get_field_value(row, "name")
            if name_val is None or str(name_val).strip() == "":
                continue

            row_name = str(name_val).strip()
            reg_name = str(record.name).strip()

            # RapidFuzz token_sort_ratio normalizes word order and casing:
            # "Rahul Sharma" vs "SHARMA RAHUL" -> 100.0
            score = float(
                fuzz.token_sort_ratio(row_name, reg_name, processor=utils.default_process)
            )

            if score < threshold:
                row_ref = context.get_field_value(row, "row_number", idx)
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="name",
                        message=(
                            f"Student name '{row_name}' does not match APAAR registry name "
                            f"'{reg_name}' (similarity {score:.1f}% is below threshold "
                            f"{threshold:.0f}%)."
                        ),
                        fix_hint=(
                            f"Verify spelling against the student's official APAAR card name "
                            f"'{reg_name}', or provide an institutional justification."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = ApaarNameMismatchRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
