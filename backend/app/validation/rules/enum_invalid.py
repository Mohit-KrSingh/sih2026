"""Validation rule: ENUM_INVALID."""

from __future__ import annotations

from typing import Any

from app.validation.codes import ENUM_INVALID
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule

ALLOWED_ENUMS: dict[str, set[str]] = {
    "gender": {"Male", "Female", "Other"},
    "reservation_category": {"General", "OBC", "SC", "ST", "EWS"},
    "seat_type": {"Regular", "Supernumerary"},
    "admission_mode": {
        "JEE Main counselling",
        "State counselling",
        "Management quota",
        "Direct second year",
        "NRI/OCI/foreign quota",
        "Other",
    },
    "nri": {"Yes", "No"},
    "oci": {"Yes", "No"},
    "foreign_national": {"Yes", "No"},
}


@register_rule
class EnumInvalidRule(BaseRule):
    """Checks that enumerated fields contain only valid AICTE permitted values."""

    code: str = ENUM_INVALID
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {
        "allowed_enums": {k: sorted(v) for k, v in ALLOWED_ENUMS.items()}
    }
    description: str = "Value not in the allowed list (gender, category, seat type, mode, Yes/No)."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        raw_enum_spec = context.get_param("allowed_enums", ALLOWED_ENUMS)
        enum_spec: dict[str, set[str]] = {
            k: set(v) if isinstance(v, (list, set, tuple)) else set()
            for k, v in raw_enum_spec.items()
        }

        for idx, row in enumerate(context.get_all_rows(), start=1):
            row_ref = context.get_field_value(row, "row_number", idx)

            for field_name, allowed_values in enum_spec.items():
                val = context.get_field_value(row, field_name)
                if val is None or str(val).strip() == "":
                    # Missing values for required fields or optional flags are evaluated separately
                    continue

                val_str = str(val).strip()
                if val_str not in allowed_values:
                    sorted_allowed = ", ".join(sorted(allowed_values))
                    flags.append(
                        Flag(
                            rule_code=self.code,
                            level=self.default_level,
                            row_ref=row_ref,
                            field=field_name,
                            message=(
                                f"Value '{val_str}' for '{field_name}' is not in the "
                                f"allowed list: {sorted_allowed}."
                            ),
                            fix_hint=f"Select one of the allowed options: {sorted_allowed}.",
                            audience=ValidationAudience.COLLEGE.value,
                            requires_justification=False,
                        )
                    )

        return flags


rule = EnumInvalidRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
