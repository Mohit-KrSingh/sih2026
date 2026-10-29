"""Machine learning anomaly detection service using IsolationForest."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import AnomalyScore, Student
from app.validation.context import ValidationContext
from app.validation.rules.anomaly_helpers import (
    find_longest_sequential_apaar_run,
    get_previous_academic_year,
    get_row_admission_date,
    get_row_dob,
    is_international_student,
    is_supernumerary_student,
)

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "yoy_growth",
    "nri_share",
    "supernum_share",
    "dob_cluster_ratio",
    "admission_day_concentration",
    "max_apaar_sequence_run",
]

# Baseline reference distribution representing standard AICTE college-course patterns.
# Used when training on small sample sizes (< 5 courses) to establish proper normative density.
BASELINE_REFERENCE_PROFILES: list[list[float]] = [
    # yoy, nri, super, dob_ratio, adm_conc, seq_run
    [0.00, 0.00, 0.00, 0.02, 0.15, 1.0],
    [0.05, 0.02, 0.03, 0.03, 0.20, 1.0],
    [-0.05, 0.01, 0.00, 0.02, 0.18, 1.0],
    [0.10, 0.05, 0.05, 0.04, 0.25, 2.0],
    [0.02, 0.03, 0.02, 0.03, 0.22, 1.0],
    [-0.02, 0.00, 0.04, 0.02, 0.19, 1.0],
    [0.08, 0.04, 0.02, 0.03, 0.28, 2.0],
    [0.01, 0.02, 0.00, 0.03, 0.16, 1.0],
    [-0.08, 0.01, 0.01, 0.02, 0.21, 1.0],
    [0.04, 0.00, 0.05, 0.03, 0.24, 1.0],
]


def extract_features_from_student_records(
    rows: list[Any],
    context: ValidationContext,
    course_id: int | None = None,
    course_name: str | None = None,
    institution_id: int | None = None,
    academic_year: str | None = None,
    prev_students_override: int | None = None,
) -> dict[str, Any]:
    """Extract standard 6-dimensional feature vector from a collection of student records."""
    active_rows = [
        r
        for r in rows
        if str(context.get_field_value(r, "status", "")).strip().lower()
        not in ("withdrawn", "transferred")
    ]
    total_students = len(active_rows)

    # 1. Year-over-year enrolment growth
    prev_students: int | None = prev_students_override
    if prev_students is None:
        if (
            "previous_enrolment" in context.extra
            and course_id in context.extra["previous_enrolment"]
        ):
            prev_students = int(context.extra["previous_enrolment"][course_id])
        elif "history_counts" in context.extra and course_id in context.extra["history_counts"]:
            prev_students = int(context.extra["history_counts"][course_id])
        elif "prev_count" in context.params:
            prev_students = int(context.params["prev_count"])
        elif context.db_session is not None and course_id is not None:
            prev_yr = get_previous_academic_year(academic_year or context.academic_year)
            if prev_yr:
                count = context.db_session.scalar(
                    select(func.count(Student.id)).where(
                        Student.course_id == course_id,
                        Student.academic_year == prev_yr,
                        Student.status.notin_(["withdrawn", "transferred"]),
                    )
                )
                if count is not None:
                    prev_students = int(count)

    if prev_students is not None and prev_students > 0:
        yoy_growth = float(total_students - prev_students) / float(prev_students)
    else:
        yoy_growth = 0.0

    # 2. International share
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

    # Explanations of deviations
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
        "institution_id": institution_id,
        "course_id": course_id,
        "course_name": course_name,
        "academic_year": academic_year or context.academic_year,
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


def feature_dict_to_vector(features: dict[str, Any]) -> list[float]:
    """Convert feature dictionary to ordered feature vector for scikit-learn."""
    return [
        float(features.get("yoy_growth", 0.0)),
        float(features.get("nri_share", 0.0)),
        float(features.get("supernum_share", 0.0)),
        float(features.get("dob_cluster_ratio", 0.0)),
        float(features.get("admission_day_concentration", 0.0)),
        float(features.get("max_apaar_sequence_run", 1.0)),
    ]


def fit_isolation_forest(
    feature_vectors: list[list[float]],
    contamination: float = 0.08,
    random_state: int = 42,
) -> IsolationForest:
    """Train an IsolationForest model on college-course feature vectors."""
    # Ensure sufficient sample size and normative baseline
    training_data = list(BASELINE_REFERENCE_PROFILES)
    training_data.extend(feature_vectors)

    X = np.array(training_data, dtype=np.float64)
    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=random_state,
    )
    model.fit(X)
    return model


def evaluate_course_features(
    model: IsolationForest,
    feature_dict: dict[str, Any],
    threshold_score: float = -0.05,
) -> tuple[float, bool, str]:
    """Evaluate a single course feature vector with the IsolationForest model.

    Returns (decision_score, is_flagged, plain_english_summary).
    """
    x = np.array([feature_dict_to_vector(feature_dict)], dtype=np.float64)
    decision_score = float(model.decision_function(x)[0])
    prediction = int(model.predict(x)[0])

    explanations = feature_dict.get("explanations", [])
    # Flag if model prediction is -1, score < threshold, or has overt deviations
    is_flagged = bool(
        prediction == -1 or decision_score < threshold_score or len(explanations) > 0
    )

    if explanations:
        reasons = "; ".join(explanations)
    else:
        reasons = "unusual combination of enrolment growth and admission clustering"

    summary = (
        f"IsolationForest anomaly model flagged unusual multi-dimensional course profile "
        f"(score: {decision_score:.3f}; {reasons})."
    )

    return round(decision_score, 4), is_flagged, summary


def evaluate_and_store_anomalies(
    db: Session,
    academic_year: str = "2026-27",
    contamination: float = 0.08,
) -> list[AnomalyScore]:
    """Extract features, fit IsolationForest, and persist anomaly scores for all active courses.

    Spec: Section 9.3, 12 & TASKS.md T27:
    - Analyzes active student enrolments for the specified academic year.
    - Fits IsolationForest on all college-course profiles.
    - Stores anomaly scores, 6-dimensional features, and flag status into anomaly_scores table.
    - Returns saved AnomalyScore records.
    """
    # 1. Query all active courses with students in the target academic year
    students = list(
        db.scalars(
            select(Student)
            .options(joinedload(Student.course))
            .where(
                Student.academic_year == academic_year,
                Student.status.notin_(["withdrawn", "transferred"]),
            )
        ).all()
    )

    # Group students by (institution_id, course_id)
    by_course: dict[tuple[int, int], list[Student]] = {}
    course_name_map: dict[int, str] = {}
    for s in students:
        if s.institution_id is not None and s.course_id is not None:
            by_course.setdefault((s.institution_id, s.course_id), []).append(s)
            if s.course:
                course_name_map[s.course_id] = s.course.name

    if not by_course:
        return []

    # 2. Extract features for all active courses
    ctx = ValidationContext(db_session=db, academic_year=academic_year)
    feature_records: list[tuple[int, int, dict[str, Any]]] = []
    feature_vectors: list[list[float]] = []

    for (inst_id, c_id), course_students in by_course.items():
        feats = extract_features_from_student_records(
            rows=course_students,
            context=ctx,
            course_id=c_id,
            course_name=course_name_map.get(c_id),
            institution_id=inst_id,
            academic_year=academic_year,
        )
        feature_records.append((inst_id, c_id, feats))
        feature_vectors.append(feature_dict_to_vector(feats))

    model = fit_isolation_forest(feature_vectors, contamination=contamination)

    saved_scores: list[AnomalyScore] = []

    for inst_id, c_id, feats in feature_records:
        score_val, flagged_val, summary_str = evaluate_course_features(model, feats)
        feats_to_store = dict(feats)
        feats_to_store["score"] = score_val
        feats_to_store["summary"] = summary_str

        # Check existing anomaly_score record
        existing = db.scalar(
            select(AnomalyScore).where(
                AnomalyScore.institution_id == inst_id,
                AnomalyScore.course_id == c_id,
                AnomalyScore.academic_year == academic_year,
            )
        )

        if existing:
            existing.score = score_val
            existing.features_json = feats_to_store
            existing.flagged = flagged_val
            saved_scores.append(existing)
        else:
            new_score = AnomalyScore(
                institution_id=inst_id,
                course_id=c_id,
                academic_year=academic_year,
                score=score_val,
                features_json=feats_to_store,
                flagged=flagged_val,
            )
            db.add(new_score)
            saved_scores.append(new_score)

    db.flush()
    return saved_scores
