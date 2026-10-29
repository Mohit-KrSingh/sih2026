"""Validation rule: DUP_SAME_COURSE_OTHER_COLLEGE."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models import Student
from app.validation.codes import DUP_SAME_COURSE_OTHER_COLLEGE
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule
from app.validation.rules.dup_active_other_college import _is_same_course


@register_rule
class DupSameCourseOtherCollegeRule(BaseRule):
    """Flags students concurrently enrolled in the same course across multiple institutions."""

    code: str = DUP_SAME_COURSE_OTHER_COLLEGE
    scope: ValidationScope = ValidationScope.CROSS
    default_level: ValidationLevel = ValidationLevel.EXCEPTION
    default_params: dict[str, Any] = {}
    description: str = "Same APAAR ID in the same course and year at another college."

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        rows = context.get_all_rows()
        if not rows:
            return flags

        inst_id = context.institution_id

        # Collect valid 12-digit APAAR IDs and row metadata
        apaar_map: dict[str, list[dict[str, Any]]] = {}
        for idx, row in enumerate(rows, start=1):
            apaar_raw = context.get_field_value(row, "apaar_id")
            if apaar_raw is None:
                continue
            apaar_str = str(apaar_raw).strip()
            if len(apaar_str) != 12 or not apaar_str.isdigit():
                continue

            year_raw = context.get_field_value(
                row, "admission_year", context.academic_year or ""
            )
            year_str = str(year_raw or "").strip()
            row_ref = context.get_field_value(row, "row_number", idx)
            row_inst = context.get_field_value(row, "institution_id", inst_id)

            apaar_map.setdefault(apaar_str, []).append(
                {
                    "idx": idx,
                    "row": row,
                    "row_ref": row_ref,
                    "institution_id": row_inst,
                    "academic_year": year_str,
                }
            )

        if not apaar_map:
            return flags

        distinct_apaars = list(apaar_map.keys())

        # 1. Check in-memory other_college_students if provided
        other_matches: list[Any] = []
        if context.other_college_students:
            for item in context.other_college_students:
                item_apaar = str(context.get_field_value(item, "apaar_id", "")).strip()
                if item_apaar not in apaar_map:
                    continue

                item_status = str(context.get_field_value(item, "status", "draft")).lower()
                if item_status in ("withdrawn", "transferred"):
                    continue

                item_inst_id = context.get_field_value(item, "institution_id")
                item_year = str(
                    context.get_field_value(item, "academic_year", "")
                ).strip()

                other_matches.append(
                    {
                        "apaar_id": item_apaar,
                        "academic_year": item_year,
                        "institution_id": item_inst_id,
                        "raw": item,
                    }
                )

        # 2. Query database if db_session is provided
        elif context.db_session is not None:
            query = (
                select(Student)
                .options(joinedload(Student.institution), joinedload(Student.course))
                .where(
                    Student.apaar_id.in_(distinct_apaars),
                    Student.status.not_in(["withdrawn", "transferred"]),
                )
            )
            if context.academic_year:
                query = query.where(Student.academic_year == str(context.academic_year))
            if inst_id is not None:
                query = query.where(Student.institution_id != inst_id)

            db_students = context.db_session.scalars(query).all()
            for s in db_students:
                other_matches.append(
                    {
                        "apaar_id": s.apaar_id,
                        "academic_year": s.academic_year,
                        "institution_id": s.institution_id,
                        "raw": s,
                    }
                )

        # 3. Match against rows where COURSE is identical
        for match in other_matches:
            match_apaar = match["apaar_id"]
            matching_rows = apaar_map.get(match_apaar, [])
            other_obj = match["raw"]

            other_inst = getattr(other_obj, "institution", None)
            if other_inst is not None:
                other_name = other_inst.name
                other_aicte_id = other_inst.aicte_id
            else:
                other_name = (
                    context.get_field_value(other_obj, "institution_name")
                    or context.get_field_value(other_obj, "other_institution_name")
                    or "another AICTE institution"
                )
                other_aicte_id = (
                    context.get_field_value(other_obj, "aicte_id")
                    or context.get_field_value(other_obj, "other_aicte_id")
                    or "AICTE-REF"
                )

            for row_info in matching_rows:
                # Do not flag against the same institution
                if (
                    match["institution_id"] is not None
                    and row_info["institution_id"] is not None
                    and match["institution_id"] == row_info["institution_id"]
                ):
                    continue

                # Must match academic year
                if (
                    match["academic_year"]
                    and row_info["academic_year"]
                    and match["academic_year"] != row_info["academic_year"]
                ):
                    continue

                # Must be the SAME course
                if not _is_same_course(context, row_info["row"], other_obj):
                    continue

                course_val = context.get_field_value(row_info["row"], "course")
                course_display = getattr(course_val, "name", str(course_val or "Same Course"))

                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_info["row_ref"],
                        field="apaar_id",
                        message=(
                            f"APAAR ID {match_apaar} is concurrently enrolled in the same course "
                            f"({course_display}) at {other_name} ({other_aicte_id}) "
                            f"for academic year {row_info['academic_year']}."
                        ),
                        fix_hint=(
                            "Student cannot be concurrently enrolled in the same programme across "
                            "multiple institutions. Provide university transfer/dual-enrolment "
                            "justification or withdraw record."
                        ),
                        audience=ValidationAudience.BOTH.value,
                        requires_justification=True,
                    )
                )

        return flags


rule = DupSameCourseOtherCollegeRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
