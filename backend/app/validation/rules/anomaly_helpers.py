"""Shared helpers for anomaly detection validation rules and feature extraction."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select

from app.auth.security import decrypt_dob
from app.models import Student
from app.validation.context import ValidationContext
from app.validation.rules.course_helpers import CourseStudentCounts


def get_row_dob(row: Any, context: ValidationContext) -> str | None:
    """Extract student date of birth as YYYY-MM-DD ISO string."""
    dob_val = context.get_field_value(row, "dob")
    if dob_val:
        if isinstance(dob_val, (date, datetime)):
            return dob_val.strftime("%Y-%m-%d")
        dob_str = str(dob_val).strip()
        if dob_str:
            return dob_str[:10]

    # Fallback to decrypting dob_encrypted on ORM Student
    dob_enc = context.get_field_value(row, "dob_encrypted")
    if dob_enc:
        try:
            dec = decrypt_dob(dob_enc)
            return dec.strftime("%Y-%m-%d")
        except Exception:
            pass

    return None


def get_row_admission_date(row: Any, context: ValidationContext) -> str | None:
    """Extract admission date as YYYY-MM-DD ISO string."""
    adm_val = context.get_field_value(row, "admission_date")
    if adm_val:
        if isinstance(adm_val, (date, datetime)):
            return adm_val.strftime("%Y-%m-%d")
        adm_str = str(adm_val).strip()
        if adm_str:
            return adm_str[:10]
    return None


def is_international_student(row: Any, context: ValidationContext) -> bool:
    """Determine whether student is admitted under international or diaspora quota."""
    nri = str(context.get_field_value(row, "nri", "")).strip().lower() in ("yes", "y", "true")
    oci = str(context.get_field_value(row, "oci", "")).strip().lower() in ("yes", "y", "true")
    fn = str(context.get_field_value(row, "foreign_national", "")).strip().lower() in (
        "yes",
        "y",
        "true",
    )
    mode = str(context.get_field_value(row, "admission_mode", "")).strip().lower()
    return nri or oci or fn or "nri" in mode or "foreign" in mode or "oci" in mode


def is_supernumerary_student(row: Any, context: ValidationContext) -> bool:
    """Determine whether student occupies a supernumerary seat."""
    seat_type = str(context.get_field_value(row, "seat_type", "")).strip().lower()
    return seat_type == "supernumerary"


def find_longest_sequential_apaar_run(
    rows: list[Any], context: ValidationContext
) -> tuple[int, str | None, str | None]:
    """Find the longest run of contiguous sequential APAAR IDs.

    Returns (run_length, start_apaar_id, end_apaar_id).
    """
    valid_aids: list[int] = []
    for r in rows:
        aid = context.get_field_value(r, "apaar_id")
        if aid is not None:
            aid_str = str(aid).strip()
            if len(aid_str) == 12 and aid_str.isdigit():
                valid_aids.append(int(aid_str))

    if not valid_aids:
        return 0, None, None

    sorted_unique = sorted(set(valid_aids))
    max_run = 1
    cur_run = 1
    run_start = sorted_unique[0]
    best_start = run_start
    best_end = run_start

    for i in range(1, len(sorted_unique)):
        if sorted_unique[i] == sorted_unique[i - 1] + 1:
            cur_run += 1
            if cur_run > max_run:
                max_run = cur_run
                best_start = run_start
                best_end = sorted_unique[i]
        else:
            run_start = sorted_unique[i]
            cur_run = 1

    if max_run > 1:
        return max_run, f"{best_start:012d}", f"{best_end:012d}"
    return 1, f"{sorted_unique[0]:012d}", f"{sorted_unique[0]:012d}"


def get_previous_academic_year(academic_year: str | None) -> str | None:
    """Calculate prior academic year string (e.g. '2026-27' -> '2025-26')."""
    if not academic_year or "-" not in academic_year:
        return None
    try:
        parts = academic_year.strip().split("-")
        start = int(parts[0])
        return f"{start - 1}-{(start) % 100:02d}"
    except Exception:
        return None


def resolve_previous_year_enrolment(
    counts: CourseStudentCounts,
    context: ValidationContext,
) -> int | None:
    """Resolve previous academic year active enrolment count for a course."""
    course_id = counts.course_id
    if course_id is None and context.course_id is not None:
        course_id = context.course_id

    # 1. Direct parameter or extra override
    if "previous_enrolment" in context.extra and course_id in context.extra["previous_enrolment"]:
        return int(context.extra["previous_enrolment"][course_id])
    if "history_counts" in context.extra and course_id in context.extra["history_counts"]:
        return int(context.extra["history_counts"][course_id])
    if "prev_count" in context.params:
        return int(context.params["prev_count"])

    # 2. Check context.history_students
    if context.history_students:
        c_name = str(counts.course_name or "").strip().lower()
        matching = 0
        for s in context.history_students:
            s_cid = context.get_field_value(s, "course_id")
            s_cname = str(context.get_field_value(s, "course", "")).strip().lower()
            if (course_id is not None and s_cid == course_id) or (c_name and s_cname == c_name):
                status = str(context.get_field_value(s, "status", "")).strip().lower()
                if status not in ("withdrawn", "transferred"):
                    matching += 1
        return matching

    # 3. Query PostgreSQL database session
    if context.db_session is not None and course_id is not None:
        prev_year = get_previous_academic_year(context.academic_year)
        if prev_year:
            count = context.db_session.scalar(
                select(func.count(Student.id)).where(
                    Student.course_id == course_id,
                    Student.academic_year == prev_year,
                    Student.status.notin_(["withdrawn", "transferred"]),
                )
            )
            if count is not None:
                return int(count)

    return None


def extract_course_anomaly_features(
    counts: CourseStudentCounts,
    context: ValidationContext,
) -> dict[str, Any]:
    """Extract standard 6-dimensional feature vector for a college-course."""
    active_rows = counts.active_rows
    total_students = len(active_rows)

    # 1. Year-over-year enrolment growth
    prev_students = resolve_previous_year_enrolment(counts, context)
    if prev_students is not None and prev_students > 0:
        yoy_growth = float(total_students - prev_students) / float(prev_students)
    else:
        yoy_growth = 0.0

    # 2. International share (NRI / OCI / Foreign National)
    intl_count = sum(1 for r in active_rows if is_international_student(r, context))
    nri_share = float(intl_count) / float(total_students) if total_students > 0 else 0.0

    # 3. Supernumerary share
    supernum_count = sum(1 for r in active_rows if is_supernumerary_student(r, context))
    supernum_share = float(supernum_count) / float(total_students) if total_students > 0 else 0.0

    # 4. DOB clustering
    dob_counter: Counter[str] = Counter()
    for r in active_rows:
        d = get_row_dob(r, context)
        if d:
            dob_counter[d] += 1
    max_dob_count = max(dob_counter.values()) if dob_counter else 0
    dob_cluster_ratio = float(max_dob_count) / float(total_students) if total_students > 0 else 0.0

    # 5. Admission-day concentration
    date_counter: Counter[str] = Counter()
    for r in active_rows:
        ad = get_row_admission_date(r, context)
        if ad:
            date_counter[ad] += 1
    max_date_count = max(date_counter.values()) if date_counter else 0
    admission_day_concentration = (
        float(max_date_count) / float(total_students) if total_students > 0 else 0.0
    )

    # 6. Sequential APAAR runs
    max_apaar_run, start_aid, end_aid = find_longest_sequential_apaar_run(active_rows, context)

    # Generate explanations for anomalous dimensions
    explanations: list[str] = []
    if yoy_growth >= 0.30:
        pct = yoy_growth * 100.0
        explanations.append(
            f"Enrolment growth +{pct:.1f}% ({prev_students} -> {total_students}) "
            "exceeds 30% threshold"
        )
    if nri_share >= 0.25:
        pct = nri_share * 100.0
        explanations.append(f"International quota share {pct:.1f}% exceeds 25% threshold")
    if supernum_share >= 0.15:
        pct = supernum_share * 100.0
        explanations.append(f"Supernumerary admission share {pct:.1f}% exceeds 15% threshold")
    if max_dob_count >= 5:
        top_dob = dob_counter.most_common(1)[0][0]
        explanations.append(f"DOB cluster of {max_dob_count} students sharing {top_dob}")
    if admission_day_concentration >= 0.60 and total_students >= 5:
        pct = admission_day_concentration * 100.0
        top_day = date_counter.most_common(1)[0][0]
        explanations.append(f"Single-day admission concentration {pct:.1f}% on {top_day}")
    if max_apaar_run >= 10:
        explanations.append(
            f"Sequential run of {max_apaar_run} APAAR IDs ({start_aid} to {end_aid})"
        )

    return {
        "course_id": counts.course_id,
        "course_name": counts.course_name,
        "total_students": total_students,
        "prev_students": prev_students,
        "yoy_growth": round(yoy_growth, 4),
        "nri_share": round(nri_share, 4),
        "supernum_share": round(supernum_share, 4),
        "max_dob_count": max_dob_count,
        "dob_cluster_ratio": round(dob_cluster_ratio, 4),
        "admission_day_concentration": round(admission_day_concentration, 4),
        "max_apaar_sequence_run": max_apaar_run,
        "explanations": explanations,
    }
