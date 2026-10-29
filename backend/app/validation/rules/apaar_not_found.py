"""Validation rule: APAAR_NOT_FOUND."""

from __future__ import annotations

import re
from typing import Any

from app.validation.apaar_lookup import get_apaar_cache
from app.validation.codes import APAAR_NOT_FOUND
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule

APAAR_REGEX = re.compile(r"^\d{12}$")


@register_rule
class ApaarNotFoundRule(BaseRule):
    """Checks that the student's APAAR ID exists in the central APAAR registry."""

    code: str = APAAR_NOT_FOUND
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = "ID does not exist in the registry."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        cache = get_apaar_cache(context)

        for idx, row in enumerate(context.get_all_rows(), start=1):
            val = context.get_field_value(row, "apaar_id")
            if val is None:
                continue
            aid = str(val).strip()
            # Cheap check first: skip format-invalid rows (handled by APAAR_REQUIRED / APAAR_FORMAT)
            if not APAAR_REGEX.match(aid):
                continue

            record = cache.get(aid)
            if record is None:
                row_ref = context.get_field_value(row, "row_number", idx)
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="apaar_id",
                        message=f"APAAR ID '{aid}' does not exist in the APAAR registry.",
                        fix_hint=(
                            "Verify the 12-digit APAAR ID with the student or request APAAR "
                            "generation through the national academic depository."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = ApaarNotFoundRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
