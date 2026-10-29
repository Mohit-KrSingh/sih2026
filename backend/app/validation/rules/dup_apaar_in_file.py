"""Validation rule: DUP_APAAR_IN_FILE."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models import Student
from app.validation.codes import DUP_APAAR_IN_FILE
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule


@register_rule
class DupApaarInFileRule(BaseRule):
    """Flags duplicate APAAR IDs within the file or existing college records for the year."""

    code: str = DUP_APAAR_IN_FILE
    scope: ValidationScope = ValidationScope.FILE
    default_level: ValidationLevel = ValidationLevel.ERROR
    default_params: dict[str, Any] = {}
    description: str = (
        "Same APAAR ID appears twice in the upload or the college's records for that year."
    )

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        rows = context.get_all_rows()
        if not rows:
            return flags

        # 1. Map rows by valid 12-digit APAAR ID
        apaar_map: dict[str, list[dict[str, Any]]] = {}
        for idx, row in enumerate(rows, start=1):
            apaar_raw = context.get_field_value(row, "apaar_id")
            if apaar_raw is None:
                continue
            apaar_str = str(apaar_raw).strip()
            if len(apaar_str) != 12 or not apaar_str.isdigit():
                continue

            row_ref = context.get_field_value(row, "row_number", idx)
            student_id = context.get_field_value(
                row, "id", context.get_field_value(row, "student_id")
            )
            year = context.get_field_value(row, "admission_year", context.academic_year)
            enrol_no = context.get_field_value(row, "enrolment_no", "")

            apaar_map.setdefault(apaar_str, []).append(
                {
                    "idx": idx,
                    "row": row,
                    "row_ref": row_ref,
                    "student_id": student_id,
                    "academic_year": year,
                    "enrolment_no": enrol_no,
                }
            )

        # 2. Check for duplicate APAAR IDs within the batch
        flagged_batch_refs: set[Any] = set()
        for apaar_id, items in apaar_map.items():
            if len(items) > 1:
                row_refs_str = ", ".join(str(it["row_ref"]) for it in items)
                for it in items:
                    flags.append(
                        Flag(
                            rule_code=self.code,
                            level=self.default_level,
                            row_ref=it["row_ref"],
                            field="apaar_id",
                            message=(
                                f"APAAR ID {apaar_id} appears multiple times "
                                f"in upload (rows {row_refs_str})."
                            ),
                            fix_hint=(
                                "Remove duplicate student rows so each APAAR ID "
                                "appears exactly once."
                            ),
                            audience=ValidationAudience.COLLEGE.value,
                            requires_justification=False,
                        )
                    )
                    flagged_batch_refs.add(it["row_ref"])

        # 3. Check against existing college records for that year
        inst_id = context.institution_id
        distinct_apaars = list(apaar_map.keys())

        if inst_id is not None and distinct_apaars:
            # 3a. Check in-memory all_college_students if provided
            if context.all_college_students:
                for existing in context.all_college_students:
                    ex_apaar = context.get_field_value(existing, "apaar_id")
                    if ex_apaar is None:
                        continue
                    ex_apaar_str = str(ex_apaar).strip()
                    if ex_apaar_str not in apaar_map:
                        continue

                    ex_year = context.get_field_value(existing, "academic_year")
                    ex_inst = context.get_field_value(existing, "institution_id")
                    if ex_inst is not None and ex_inst != inst_id:
                        continue

                    ex_status = context.get_field_value(existing, "status")
                    if ex_status in ("withdrawn", "transferred"):
                        continue

                    ex_id = context.get_field_value(
                        existing, "id", context.get_field_value(existing, "student_id")
                    )
                    ex_enrol = context.get_field_value(existing, "enrolment_no", "")

                    for it in apaar_map[ex_apaar_str]:
                        if it["row_ref"] in flagged_batch_refs:
                            continue
                        # If same student record being updated, do not flag
                        if (
                            ex_id is not None
                            and it["student_id"] is not None
                            and str(ex_id) == str(it["student_id"])
                        ):
                            continue
                        # Verify matching academic year
                        if (
                            ex_year
                            and it["academic_year"]
                            and str(ex_year) != str(it["academic_year"])
                        ):
                            continue

                        flags.append(
                            Flag(
                                rule_code=self.code,
                                level=self.default_level,
                                row_ref=it["row_ref"],
                                field="apaar_id",
                                message=(
                                    f"APAAR ID {ex_apaar_str} already exists in college "
                                    f"records for academic year {it['academic_year']} "
                                    f"(enrolment: {ex_enrol})."
                                ),
                                fix_hint=(
                                    "Update the existing student record instead of "
                                    "adding a duplicate entry."
                                ),
                                audience=ValidationAudience.COLLEGE.value,
                                requires_justification=False,
                            )
                        )
                        flagged_batch_refs.add(it["row_ref"])

            # 3b. Query database if db_session is provided and not already checked
            elif context.db_session is not None:
                query = select(Student).where(
                    Student.institution_id == inst_id,
                    Student.apaar_id.in_(distinct_apaars),
                    Student.status.not_in(["withdrawn", "transferred"]),
                )
                if context.academic_year:
                    query = query.where(Student.academic_year == str(context.academic_year))

                existing_students = context.db_session.scalars(query).all()
                for ex_student in existing_students:
                    ex_apaar_str = ex_student.apaar_id
                    if ex_apaar_str not in apaar_map:
                        continue
                    for it in apaar_map[ex_apaar_str]:
                        if it["row_ref"] in flagged_batch_refs:
                            continue
                        if it["student_id"] is not None and str(ex_student.id) == str(
                            it["student_id"]
                        ):
                            continue
                        if (
                            ex_student.academic_year
                            and it["academic_year"]
                            and str(ex_student.academic_year) != str(it["academic_year"])
                        ):
                            continue

                        flags.append(
                            Flag(
                                rule_code=self.code,
                                level=self.default_level,
                                row_ref=it["row_ref"],
                                field="apaar_id",
                                message=(
                                    f"APAAR ID {ex_apaar_str} already exists in college "
                                    f"records for academic year {it['academic_year']} "
                                    f"(enrolment: {ex_student.enrolment_no})."
                                ),
                                fix_hint=(
                                    "Update the existing student record instead of "
                                    "adding a duplicate entry."
                                ),
                                audience=ValidationAudience.COLLEGE.value,
                                requires_justification=False,
                            )
                        )
                        flagged_batch_refs.add(it["row_ref"])

        return flags


rule = DupApaarInFileRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
