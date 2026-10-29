"""Validation rule: MODE_CATEGORY_MISMATCH."""

from __future__ import annotations

import re
from typing import Any

from app.validation.codes import MODE_CATEGORY_MISMATCH
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule


def _is_nri_quota_mode(mode_val: Any) -> bool:
    """Check if admission mode corresponds to NRI/OCI/foreign quota."""
    if not mode_val:
        return False
    norm = re.sub(r"\s+", " ", str(mode_val).strip().lower())
    norm = re.sub(r"\s*/\s*", "/", norm)
    return norm in (
        "nri/oci/foreign quota",
        "nri/oci/foreign",
        "nri quota",
        "foreign quota",
    )


@register_rule
class ModeCategoryMismatchRule(BaseRule):
    """Checks consistency between student international status and admission mode."""

    code: str = MODE_CATEGORY_MISMATCH
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.WARNING
    default_params: dict[str, Any] = {}
    description: str = (
        "NRI/OCI/foreign student not admitted through the NRI/OCI/foreign quota, "
        "or the reverse."
    )

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []

        for idx, row in enumerate(context.get_all_rows(), start=1):
            adm_mode = context.get_field_value(row, "admission_mode")
            nri_val = context.get_field_value(row, "nri")
            oci_val = context.get_field_value(row, "oci")
            fn_val = context.get_field_value(row, "foreign_national")

            # Skip rows where admission mode or categories are not populated
            if adm_mode is None and nri_val is None and oci_val is None and fn_val is None:
                continue

            is_nri = nri_val is not None and str(nri_val).strip().lower() == "yes"
            is_oci = oci_val is not None and str(oci_val).strip().lower() == "yes"
            is_fn = fn_val is not None and str(fn_val).strip().lower() == "yes"
            has_intl_status = is_nri or is_oci or is_fn
            is_intl_quota = _is_nri_quota_mode(adm_mode)

            row_ref = context.get_field_value(row, "row_number", idx)
            requires_justification = bool(context.get_param("requires_justification", False))

            # Case 1: Student is NRI/OCI/FN but NOT admitted via NRI/OCI/foreign quota
            if has_intl_status and not is_intl_quota:
                tags: list[str] = []
                if is_nri:
                    tags.append("NRI")
                if is_oci:
                    tags.append("OCI")
                if is_fn:
                    tags.append("Foreign National")
                tag_display = "/".join(tags)

                mode_display = str(adm_mode).strip() if adm_mode else "None"
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="admission_mode",
                        message=(
                            f"Student is marked as {tag_display} status but admitted through "
                            f"'{mode_display}' instead of 'NRI/OCI/foreign quota'."
                        ),
                        fix_hint=(
                            "Change admission mode to 'NRI/OCI/foreign quota' or verify "
                            "student category flags."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=requires_justification,
                    )
                )

            # Case 2: Admitted via NRI quota but NO international flag is Yes (the reverse)
            elif is_intl_quota and not has_intl_status:
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="admission_mode",
                        message=(
                            "Student admitted under 'NRI/OCI/foreign quota' but none of "
                            "NRI, OCI, or Foreign National are marked 'Yes'."
                        ),
                        fix_hint=(
                            "Mark the applicable NRI, OCI, or Foreign National status to 'Yes', "
                            "or update admission mode if admitted through another quota."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=requires_justification,
                    )
                )

        return flags


rule = ModeCategoryMismatchRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
