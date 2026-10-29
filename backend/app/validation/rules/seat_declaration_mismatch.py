"""Validation rule: SEAT_DECLARATION_MISMATCH."""

from __future__ import annotations

from typing import Any

from app.validation.codes import SEAT_DECLARATION_MISMATCH
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule
from app.validation.rules.course_helpers import (
    get_course_student_counts,
    resolve_declared_seats,
)


@register_rule
class SeatDeclarationMismatchRule(BaseRule):
    """Flags when college-declared seat totals do not reconcile with actual student records."""

    code: str = SEAT_DECLARATION_MISMATCH
    scope: ValidationScope = ValidationScope.COURSE
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = (
        "Declared counts differ from uploaded student list. "
        "Blocks submit; college fixes either side."
    )

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        course_groups = get_course_student_counts(context)

        for _group_key, counts in course_groups.items():
            declared = resolve_declared_seats(counts, context)
            if not declared:
                continue

            differences: list[str] = []

            # Compare regular admitted
            if "regular_admitted" in declared:
                decl_reg = declared["regular_admitted"]
                if decl_reg != counts.regular_count:
                    differences.append(
                        f"regular admitted (declared {decl_reg} vs actual {counts.regular_count})"
                    )

            # Compare supernumerary admitted
            if "supernumerary_admitted" in declared:
                decl_sup = declared["supernumerary_admitted"]
                if decl_sup != counts.supernumerary_count:
                    differences.append(
                        f"supernumerary admitted (declared {decl_sup} vs "
                        f"actual {counts.supernumerary_count})"
                    )

            # Compare NRI admitted if declared
            if "nri_count" in declared:
                decl_nri = declared["nri_count"]
                if decl_nri != counts.nri_count:
                    differences.append(
                        f"NRI admitted (declared {decl_nri} vs actual {counts.nri_count})"
                    )

            # Compare OCI admitted if declared
            if "oci_count" in declared:
                decl_oci = declared["oci_count"]
                if decl_oci != counts.oci_count:
                    differences.append(
                        f"OCI admitted (declared {decl_oci} vs actual {counts.oci_count})"
                    )

            # Compare Foreign National admitted if declared
            if "fn_count" in declared:
                decl_fn = declared["fn_count"]
                if decl_fn != counts.fn_count:
                    differences.append(
                        f"foreign national admitted (declared {decl_fn} vs "
                        f"actual {counts.fn_count})"
                    )

            if differences:
                course_desc = (
                    f" for course '{counts.course_name}'" if counts.course_name else ""
                )
                message = (
                    f"Declared seat counts{course_desc} do not match uploaded student records: "
                    f"{'; '.join(differences)}."
                )
                fix_hint = (
                    "Update your seat declaration counts to reflect actual admissions "
                    "or adjust the uploaded student records."
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
                        field="seat_declaration",
                        message=message,
                        fix_hint=fix_hint,
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = SeatDeclarationMismatchRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
