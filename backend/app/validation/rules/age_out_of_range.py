"""Validation rule: AGE_OUT_OF_RANGE."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.validation.codes import AGE_OUT_OF_RANGE
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule

DEFAULT_BANDS: dict[str, tuple[int, int]] = {
    "UG": (15, 30),
    "PG": (19, 45),
    "Diploma": (14, 30),
    "PGDM": (19, 45),
}


def _parse_date(val: Any) -> date | None:
    """Parse date from date, datetime, or ISO string."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        return date.fromisoformat(str(val).strip())
    except (ValueError, TypeError):
        return None


def _resolve_course_level(row: Any, context: ValidationContext) -> str:
    """Resolve program level (UG | PG | Diploma | PGDM) from row or context."""
    # 1. Direct row level
    row_level = context.get_field_value(row, "level")
    if row_level and str(row_level).strip():
        norm = str(row_level).strip().upper()
        if norm in ("UG", "PG", "DIPLOMA", "PGDM"):
            return "Diploma" if norm == "DIPLOMA" else norm

    # 2. Context course level
    if context.course is not None:
        c_level = (
            getattr(context.course, "level", None)
            if not isinstance(context.course, dict)
            else context.course.get("level")
        )
        if c_level:
            norm = str(c_level).strip().upper()
            if norm in ("UG", "PG", "DIPLOMA", "PGDM"):
                return "Diploma" if norm == "DIPLOMA" else norm

    # 3. Extra approved courses match
    appr_courses = context.extra.get("approved_courses")
    if appr_courses:
        row_course = context.get_field_value(row, "course") or context.get_field_value(
            row, "course_name"
        )
        row_branch = context.get_field_value(row, "branch")
        row_course_id = context.get_field_value(row, "course_id")
        for appr in appr_courses:
            appr_id = getattr(appr, "id", None) if not isinstance(appr, dict) else appr.get("id")
            appr_name = (
                getattr(appr, "name", None) if not isinstance(appr, dict) else appr.get("name")
            )
            appr_branch = (
                getattr(appr, "branch", None) if not isinstance(appr, dict) else appr.get("branch")
            )
            appr_lvl = (
                getattr(appr, "level", None) if not isinstance(appr, dict) else appr.get("level")
            )

            id_match = (
                row_course_id is not None
                and appr_id is not None
                and str(row_course_id) == str(appr_id)
            )
            name_match = (
                row_course is not None
                and appr_name is not None
                and str(row_course).strip().lower() == str(appr_name).strip().lower()
                and (
                    row_branch is None
                    or appr_branch is None
                    or str(row_branch).strip().lower() == str(appr_branch).strip().lower()
                )
            )
            if (id_match or name_match) and appr_lvl:
                norm = str(appr_lvl).strip().upper()
                if norm in ("UG", "PG", "DIPLOMA", "PGDM"):
                    return "Diploma" if norm == "DIPLOMA" else norm

    # 4. Infer from course name if available
    course_name = (
        context.get_field_value(row, "course")
        or context.get_field_value(row, "course_name")
        or ""
    )
    c_lower = str(course_name).strip().lower()
    if "diploma" in c_lower or "polytechnic" in c_lower:
        return "Diploma"
    if "pgdm" in c_lower:
        return "PGDM"
    if any(k in c_lower for k in ("m.tech", "mca", "mba", "m.sc", "m.pharm", "post graduate")):
        return "PG"

    # Default fallback
    return "UG"


@register_rule
class AgeOutOfRangeRule(BaseRule):
    """Checks that a student's age at admission falls within standard program age bands."""

    code: str = AGE_OUT_OF_RANGE
    scope: ValidationScope = ValidationScope.ROW
    default_level: ValidationLevel = ValidationLevel.WARNING
    default_params: dict[str, Any] = {"bands": DEFAULT_BANDS}
    description: str = (
        "Age outside the course-level band (defaults: UG 15-30, PG 19-45, "
        "Diploma 14-30, PGDM 19-45)."
    )

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        bands: dict[str, tuple[int, int]] = context.get_param("bands", DEFAULT_BANDS)

        for idx, row in enumerate(context.get_all_rows(), start=1):
            dob_raw = context.get_field_value(row, "dob")
            dob = _parse_date(dob_raw)
            if dob is None:
                # Format or missing date handled by DOB_INVALID / DOB_REQUIRED
                continue

            # Determine reference date for age calculation (admission date or mid-academic year)
            adm_raw = context.get_field_value(row, "admission_date")
            adm_date = _parse_date(adm_raw)

            if adm_date is not None:
                ref_date = adm_date
            else:
                year_val = (
                    context.get_field_value(row, "admission_year") or context.academic_year
                )
                m = re.search(r"(\d{4})", str(year_val)) if year_val else None
                if m:
                    ref_date = date(int(m.group(1)), 7, 1)
                else:
                    ref_date = date.today()

            # Calculate completed chronological age
            age = (
                ref_date.year
                - dob.year
                - ((ref_date.month, ref_date.day) < (dob.month, dob.day))
            )

            level = _resolve_course_level(row, context)

            # Match level in bands dictionary (case-insensitive keys)
            band = bands.get(level)
            if band is None:
                for k, v in bands.items():
                    if k.strip().upper() == level.upper():
                        band = v
                        break
            if band is None:
                band = bands.get("UG", (15, 30))

            min_age, max_age = band[0], band[1]

            # Param overrides for min_age / max_age
            override_min = context.get_param("min_age")
            override_max = context.get_param("max_age")
            if override_min is not None:
                min_age = int(override_min)
            if override_max is not None:
                max_age = int(override_max)

            if age < min_age or age > max_age:
                row_ref = context.get_field_value(row, "row_number", idx)
                requires_justification = bool(context.get_param("requires_justification", False))
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="dob",
                        message=(
                            f"Student age of {age} years is outside the standard "
                            f"{level} age band ({min_age}-{max_age} years)."
                        ),
                        fix_hint=(
                            f"Verify student date of birth ({dob.isoformat()}) or submit "
                            f"institutional justification for {level} eligibility."
                        ),
                        audience=ValidationAudience.COLLEGE.value,
                        requires_justification=requires_justification,
                    )
                )

        return flags


rule = AgeOutOfRangeRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
