"""Comprehensive test suite for anomaly detection rules and IsolationForest ML service.

Spec: Section 9.3 & TASKS.md T27:
- Unit tests for all 7 anomaly rules: pass, fail, edge case.
- Integration tests detecting planted anomalies in seeded database:
  - BNITS CSE enrolment jump (ANOM_ENROLMENT_JUMP)
  - Mysuru Royal Mechanical DOB cluster (ANOM_DOB_CLUSTER)
  - Hubballi sequential APAAR run (ANOM_SEQUENTIAL_APAAR)
- Low false positive checks on clean colleges.
- Database persistence in anomaly_scores table.
- RBAC and API endpoint tests (GET /api/v1/analytics/anomalies).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.anomaly_service import (
    evaluate_and_store_anomalies,
    extract_features_from_student_records,
    feature_dict_to_vector,
)
from app.auth.security import create_access_token
from app.models import AnomalyScore, Course, Institution, Student, User
from app.seed import seed_all
from app.validation.codes import (
    ANOM_DOB_CLUSTER,
    ANOM_ENROLMENT_JUMP,
    ANOM_MODEL_SCORE,
    ANOM_NRI_SHARE,
    ANOM_SAME_ADMISSION_DAY,
    ANOM_SEQUENTIAL_APAAR,
    ANOM_SUPERNUM_SHARE,
)
from app.validation.context import ValidationContext
from app.validation.engine import run_rules

# =============================================================================
# 1. Unit Tests: ANOM_ENROLMENT_JUMP
# =============================================================================

def test_anom_enrolment_jump_pass():
    """Moderate enrolment growth (+10%) should pass without warning."""
    rows = [{"apaar_id": f"2000000{i:05d}", "course_id": 101} for i in range(1, 56)]  # 55 students
    ctx = ValidationContext(
        rows=rows,
        course_id=101,
        academic_year="2026-27",
        extra={"previous_enrolment": {101: 50}},  # 50 -> 55 = +10%
    )
    result = run_rules(ctx, rules=[ANOM_ENROLMENT_JUMP])
    assert len(result) == 0


def test_anom_enrolment_jump_fail():
    """Enrolment jumping 100% (50 -> 100) should trigger ANOM_ENROLMENT_JUMP."""
    # 100 students
    rows = [{"apaar_id": f"2000000{i:05d}", "course_id": 101} for i in range(1, 101)]
    ctx = ValidationContext(
        rows=rows,
        course_id=101,
        academic_year="2026-27",
        extra={"previous_enrolment": {101: 50}},
    )
    result = run_rules(ctx, rules=[ANOM_ENROLMENT_JUMP])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == ANOM_ENROLMENT_JUMP
    assert flag.level == "warning"
    assert flag.audience == "aicte"
    assert "jumped from 50 in 2025-26 to 100 in 2026-27 (+100.0%)" in flag.message


def test_anom_enrolment_jump_edge():
    """No previous enrolment or 0 previous enrolment safely skips jump detection."""
    rows = [{"apaar_id": f"2000000{i:05d}", "course_id": 101} for i in range(1, 60)]
    ctx = ValidationContext(
        rows=rows,
        course_id=101,
        academic_year="2026-27",
        extra={"previous_enrolment": {101: 0}},
    )
    result = run_rules(ctx, rules=[ANOM_ENROLMENT_JUMP])
    assert len(result) == 0

    # Overridden threshold
    ctx_override = ValidationContext(
        rows=rows,
        course_id=101,
        academic_year="2026-27",
        extra={"previous_enrolment": {101: 40}},  # 40 -> 60 = +50%
        params={"threshold_percent": 60.0},  # Threshold raised to 60%
    )
    result2 = run_rules(ctx_override, rules=[ANOM_ENROLMENT_JUMP])
    assert len(result2) == 0


# =============================================================================
# 2. Unit Tests: ANOM_NRI_SHARE
# =============================================================================

def test_anom_nri_share_pass():
    """International student share <= 25% should pass cleanly."""
    rows = []
    for i in range(1, 21):  # 20 students
        nri_val = "Yes" if i <= 3 else "No"  # 3 of 20 = 15%
        rows.append({"apaar_id": f"2000000{i:05d}", "course_id": 102, "nri": nri_val})

    ctx = ValidationContext(rows=rows, course_id=102)
    result = run_rules(ctx, rules=[ANOM_NRI_SHARE])
    assert len(result) == 0


def test_anom_nri_share_fail():
    """International student share > 25% should trigger ANOM_NRI_SHARE."""
    rows = []
    for i in range(1, 21):  # 20 students
        nri_val = "Yes" if i <= 7 else "No"  # 7 of 20 = 35%
        rows.append({"apaar_id": f"2000000{i:05d}", "course_id": 102, "nri": nri_val})

    ctx = ValidationContext(rows=rows, course_id=102)
    result = run_rules(ctx, rules=[ANOM_NRI_SHARE])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == ANOM_NRI_SHARE
    assert flag.level == "warning"
    assert flag.audience == "aicte"
    assert "35.0% (7 of 20 students)" in flag.message


def test_anom_nri_share_edge():
    """Empty rows or OCI/Foreign National combinations are accounted for."""
    ctx_empty = ValidationContext(rows=[], course_id=102)
    assert len(run_rules(ctx_empty, rules=[ANOM_NRI_SHARE])) == 0

    # Foreign national and admission mode detection
    rows = [
        {"apaar_id": "200000000001", "course_id": 102, "foreign_national": "Yes"},
        {"apaar_id": "200000000002", "course_id": 102, "oci": "Yes"},
        {"apaar_id": "200000000003", "course_id": 102, "admission_mode": "NRI/OCI/foreign quota"},
        {"apaar_id": "200000000004", "course_id": 102, "nri": "No"},
    ]  # 3 of 4 = 75%
    ctx = ValidationContext(rows=rows, course_id=102)
    result = run_rules(ctx, rules=[ANOM_NRI_SHARE])
    assert len(result) == 1
    assert "75.0%" in result[0].message


# =============================================================================
# 3. Unit Tests: ANOM_SUPERNUM_SHARE
# =============================================================================

def test_anom_supernum_share_pass():
    """Supernumerary share <= 15% should pass cleanly."""
    rows = []
    for i in range(1, 21):
        st = "Supernumerary" if i <= 2 else "Regular"  # 2 of 20 = 10%
        rows.append({"apaar_id": f"2000000{i:05d}", "course_id": 103, "seat_type": st})

    ctx = ValidationContext(rows=rows, course_id=103)
    result = run_rules(ctx, rules=[ANOM_SUPERNUM_SHARE])
    assert len(result) == 0


def test_anom_supernum_share_fail():
    """Supernumerary share > 15% should trigger ANOM_SUPERNUM_SHARE."""
    rows = []
    for i in range(1, 21):
        st = "Supernumerary" if i <= 5 else "Regular"  # 5 of 20 = 25%
        rows.append({"apaar_id": f"2000000{i:05d}", "course_id": 103, "seat_type": st})

    ctx = ValidationContext(rows=rows, course_id=103)
    result = run_rules(ctx, rules=[ANOM_SUPERNUM_SHARE])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == ANOM_SUPERNUM_SHARE
    assert flag.level == "warning"
    assert flag.audience == "aicte"
    assert "25.0% (5 of 20 students)" in flag.message


def test_anom_supernum_share_edge():
    """Threshold overrides work properly."""
    rows = []
    for i in range(1, 21):
        st = "Supernumerary" if i <= 4 else "Regular"  # 4 of 20 = 20%
        rows.append({"apaar_id": f"2000000{i:05d}", "course_id": 103, "seat_type": st})

    ctx = ValidationContext(rows=rows, course_id=103, params={"threshold_percent": 25.0})
    result = run_rules(ctx, rules=[ANOM_SUPERNUM_SHARE])
    assert len(result) == 0


# =============================================================================
# 4. Unit Tests: ANOM_DOB_CLUSTER
# =============================================================================

def test_anom_dob_cluster_pass():
    """Dispersed dates of birth (< 5 per date) should pass cleanly."""
    rows = [
        {"apaar_id": f"2000000{i:05d}", "course_id": 104, "dob": f"2004-05-{10 + (i % 4):02d}"}
        for i in range(1, 13)
    ]
    ctx = ValidationContext(rows=rows, course_id=104)
    result = run_rules(ctx, rules=[ANOM_DOB_CLUSTER])
    assert len(result) == 0


def test_anom_dob_cluster_fail():
    """Cluster of 7 students sharing identical DOB should trigger ANOM_DOB_CLUSTER."""
    rows = []
    for i in range(1, 15):
        d_val = "2005-08-15" if i <= 7 else f"2005-01-{i:02d}"
        rows.append({"apaar_id": f"2000000{i:05d}", "course_id": 104, "dob": d_val})

    ctx = ValidationContext(rows=rows, course_id=104)
    result = run_rules(ctx, rules=[ANOM_DOB_CLUSTER])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == ANOM_DOB_CLUSTER
    assert flag.level == "warning"
    assert flag.audience == "aicte"
    assert "Cluster of 7 students" in flag.message
    assert "2005-08-15" in flag.message


def test_anom_dob_cluster_edge():
    """Missing or empty DOB values are handled safely."""
    rows = [
        {"apaar_id": "200000000001", "course_id": 104, "dob": None},
        {"apaar_id": "200000000002", "course_id": 104, "dob": ""},
        {"apaar_id": "200000000003", "course_id": 104, "dob": "invalid-date"},
    ]
    ctx = ValidationContext(rows=rows, course_id=104)
    result = run_rules(ctx, rules=[ANOM_DOB_CLUSTER])
    assert len(result) == 0


# =============================================================================
# 5. Unit Tests: ANOM_SEQUENTIAL_APAAR
# =============================================================================

def test_anom_sequential_apaar_pass():
    """Non-sequential APAAR IDs should pass cleanly."""
    aids = ["100000000001", "100000000050", "100000000120", "200000000500"]
    rows = [{"apaar_id": a, "course_id": 105} for a in aids]
    ctx = ValidationContext(rows=rows, course_id=105)
    result = run_rules(ctx, rules=[ANOM_SEQUENTIAL_APAAR])
    assert len(result) == 0


def test_anom_sequential_apaar_fail():
    """Sequential run of 12 contiguous APAAR IDs should trigger ANOM_SEQUENTIAL_APAAR."""
    aids = [f"990000000{i:03d}" for i in range(101, 113)]  # 12 sequential IDs
    rows = [{"apaar_id": a, "course_id": 105} for a in aids]
    ctx = ValidationContext(rows=rows, course_id=105)
    result = run_rules(ctx, rules=[ANOM_SEQUENTIAL_APAAR])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == ANOM_SEQUENTIAL_APAAR
    assert flag.level == "warning"
    assert flag.audience == "aicte"
    assert "Sequential run of 12 APAAR IDs detected" in flag.message
    assert "990000000101 to 990000000112" in flag.message


def test_anom_sequential_apaar_edge():
    """Out-of-order, duplicate, or non-numeric IDs are sorted and handled."""
    aids = [
        "990000000105",
        "990000000101",
        "990000000102",
        "990000000103",
        "990000000104",
        "990000000102",  # dupe
        "invalid_id",  # malformed
    ]
    rows = [{"apaar_id": a, "course_id": 105} for a in aids]
    ctx = ValidationContext(rows=rows, course_id=105, params={"threshold_run": 5})
    result = run_rules(ctx, rules=[ANOM_SEQUENTIAL_APAAR])
    assert len(result) == 1
    assert "Sequential run of 5 APAAR IDs detected" in result[0].message


# =============================================================================
# 6. Unit Tests: ANOM_SAME_ADMISSION_DAY
# =============================================================================

def test_anom_same_admission_day_pass():
    """Admissions distributed across multiple dates should pass cleanly."""
    rows = [
        {"apaar_id": f"2000000{i:05d}", "course_id": 106, "admission_date": f"2026-07-{10 + i:02d}"}
        for i in range(1, 11)
    ]
    ctx = ValidationContext(rows=rows, course_id=106)
    result = run_rules(ctx, rules=[ANOM_SAME_ADMISSION_DAY])
    assert len(result) == 0


def test_anom_same_admission_day_fail():
    """75% of admissions on a single calendar day should trigger ANOM_SAME_ADMISSION_DAY."""
    rows = []
    for i in range(1, 21):
        d_val = "2026-07-25" if i <= 15 else f"2026-07-{i:02d}"  # 15 of 20 = 75%
        rows.append({"apaar_id": f"2000000{i:05d}", "course_id": 106, "admission_date": d_val})

    ctx = ValidationContext(rows=rows, course_id=106)
    result = run_rules(ctx, rules=[ANOM_SAME_ADMISSION_DAY])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == ANOM_SAME_ADMISSION_DAY
    assert flag.level == "info"
    assert flag.audience == "aicte"
    assert "75.0% of students (15 of 20) admitted on a single date (2026-07-25)" in flag.message


def test_anom_same_admission_day_edge():
    """Cohorts smaller than min_students (< 5) are excluded from concentration alert."""
    rows = [
        {"apaar_id": "200000000001", "course_id": 106, "admission_date": "2026-07-20"},
        {"apaar_id": "200000000002", "course_id": 106, "admission_date": "2026-07-20"},
    ]  # 2 of 2 = 100%, but total < 5
    ctx = ValidationContext(rows=rows, course_id=106)
    result = run_rules(ctx, rules=[ANOM_SAME_ADMISSION_DAY])
    assert len(result) == 0


# =============================================================================
# 7. Unit Tests: ANOM_MODEL_SCORE & Feature Extraction
# =============================================================================

def test_feature_extraction_and_vectorization():
    """Feature extraction extracts exactly 6 dimensions with sensible metrics."""
    rows = [
        {
            "apaar_id": "990000000101",
            "course_id": 107,
            "dob": "2005-08-15",
            "admission_date": "2026-07-15",
            "nri": "Yes",
            "seat_type": "Supernumerary",
        },
        {
            "apaar_id": "990000000102",
            "course_id": 107,
            "dob": "2005-08-15",
            "admission_date": "2026-07-15",
            "nri": "No",
            "seat_type": "Regular",
        },
    ]
    ctx = ValidationContext(rows=rows, course_id=107, extra={"previous_enrolment": {107: 1}})
    feats = extract_features_from_student_records(
        rows=rows,
        context=ctx,
        course_id=107,
        course_name="CSE",
    )

    assert feats["total_students"] == 2
    assert feats["prev_students"] == 1
    assert feats["yoy_growth"] == 1.0  # +100%
    assert feats["nri_share"] == 0.5  # 1 of 2
    assert feats["supernum_share"] == 0.5  # 1 of 2
    assert feats["max_dob_count"] == 2
    assert feats["dob_cluster_ratio"] == 1.0
    assert feats["admission_day_concentration"] == 1.0
    assert feats["max_apaar_sequence_run"] == 2

    vec = feature_dict_to_vector(feats)
    assert len(vec) == 6
    assert vec[0] == 1.0


def test_anom_model_score_detection():
    """Extreme multi-dimensional profile is flagged by IsolationForest."""
    rows = []
    # 20 students, all admitted on same day, with 15 sequential APAARs, +100% growth
    for i in range(1, 21):
        rows.append(
            {
                "apaar_id": f"990000000{i:03d}",
                "course_id": 108,
                "dob": "2005-08-15" if i <= 10 else "2005-01-01",
                "admission_date": "2026-07-20",
                "nri": "Yes" if i <= 8 else "No",
                "seat_type": "Supernumerary" if i <= 6 else "Regular",
            }
        )

    ctx = ValidationContext(
        rows=rows,
        course_id=108,
        academic_year="2026-27",
        extra={"previous_enrolment": {108: 10}},  # 10 -> 20 = +100%
    )

    result = run_rules(ctx, rules=[ANOM_MODEL_SCORE])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == ANOM_MODEL_SCORE
    assert flag.level == "warning"
    assert flag.audience == "aicte"
    assert "IsolationForest anomaly model flagged unusual" in flag.message


# =============================================================================
# 8. Database Integration: Planted Seed Anomalies & False Positives
# =============================================================================

def test_detect_planted_anomalies_in_seeded_db(db_session: Session):
    """Verify that all planted anomalies in seeded database are successfully detected."""
    seed_all(db_session)
    # 1. College 4 (BNITS, 1-10000004) CSE: +100% enrolment jump
    bnits = db_session.scalar(select(Institution).where(Institution.aicte_id == "1-10000004"))
    assert bnits is not None
    bnits_cse = db_session.scalars(
        select(Course).where(
            Course.institution_id == bnits.id,
            Course.name.ilike("%Computer Science%"),
        )
    ).first()
    assert bnits_cse is not None

    bnits_students = list(
        db_session.scalars(
            select(Student).where(
                Student.institution_id == bnits.id,
                Student.course_id == bnits_cse.id,
                Student.academic_year == "2026-27",
            )
        ).all()
    )
    assert len(bnits_students) == 160  # 80 in 2025-26 -> 160 in 2026-27

    ctx_bnits = ValidationContext(
        rows=[{"apaar_id": s.apaar_id, "course_id": s.course_id} for s in bnits_students],
        course_id=bnits_cse.id,
        institution_id=bnits.id,
        academic_year="2026-27",
        db_session=db_session,
    )
    res_jump = run_rules(ctx_bnits, rules=[ANOM_ENROLMENT_JUMP])
    assert len(res_jump) >= 1
    assert any("jumped from " in f.message for f in res_jump)

    # 2. College 5 (Mysuru Royal, 1-10000005) Mechanical:
    # Clustered DOB (8 students sharing 2005-08-15)
    mysuru = db_session.scalar(select(Institution).where(Institution.aicte_id == "1-10000005"))
    assert mysuru is not None
    mysuru_mech = db_session.scalars(
        select(Course).where(Course.institution_id == mysuru.id).order_by(Course.id)
    ).first()
    assert mysuru_mech is not None

    mysuru_students = list(
        db_session.scalars(
            select(Student).where(
                Student.institution_id == mysuru.id,
                Student.course_id == mysuru_mech.id,
                Student.academic_year == "2026-27",
            )
        ).all()
    )
    assert len(mysuru_students) >= 40

    ctx_mysuru = ValidationContext(
        all_college_students=mysuru_students,
        course_id=mysuru_mech.id,
        institution_id=mysuru.id,
        academic_year="2026-27",
        db_session=db_session,
    )
    res_dob = run_rules(ctx_mysuru, rules=[ANOM_DOB_CLUSTER])
    assert len(res_dob) >= 1
    assert any("2005-08-15" in f.message for f in res_dob)

    # 3. College 6 (Hubballi, 1-10000006): Sequential APAARs (12 consecutive IDs)
    hubballi = db_session.scalar(select(Institution).where(Institution.aicte_id == "1-10000006"))
    assert hubballi is not None
    hubballi_course = db_session.scalars(
        select(Course).where(Course.institution_id == hubballi.id).order_by(Course.id)
    ).first()
    assert hubballi_course is not None

    hubballi_students = list(
        db_session.scalars(
            select(Student).where(
                Student.institution_id == hubballi.id,
                Student.course_id == hubballi_course.id,
                Student.academic_year == "2026-27",
            )
        ).all()
    )
    ctx_hubballi = ValidationContext(
        all_college_students=hubballi_students,
        course_id=hubballi_course.id,
        institution_id=hubballi.id,
        academic_year="2026-27",
        db_session=db_session,
    )
    res_seq = run_rules(ctx_hubballi, rules=[ANOM_SEQUENTIAL_APAAR])
    assert len(res_seq) >= 1
    assert any("Sequential run of 12 APAAR IDs" in f.message for f in res_seq)

    # 4. Low false positives on Clean College 1 (Pune Institute CSE)
    pune = db_session.scalar(select(Institution).where(Institution.aicte_id == "1-10000001"))
    assert pune is not None
    pune_cse = db_session.scalars(
        select(Course).where(Course.institution_id == pune.id).order_by(Course.id)
    ).first()
    assert pune_cse is not None

    pune_students = list(
        db_session.scalars(
            select(Student).where(
                Student.institution_id == pune.id,
                Student.course_id == pune_cse.id,
                Student.academic_year == "2026-27",
            )
        ).all()
    )
    ctx_pune = ValidationContext(
        all_college_students=pune_students,
        course_id=pune_cse.id,
        institution_id=pune.id,
        academic_year="2026-27",
        db_session=db_session,
    )
    # None of the enrolment, demographic or quota anomaly warnings should trigger on clean college
    res_pune = run_rules(
        ctx_pune,
        rules=[
            ANOM_ENROLMENT_JUMP,
            ANOM_NRI_SHARE,
            ANOM_SUPERNUM_SHARE,
            ANOM_DOB_CLUSTER,
        ],
    )
    assert len(res_pune) == 0


def test_evaluate_and_store_anomalies_service(db_session: Session):
    """Verify evaluate_and_store_anomalies stores scores into anomaly_scores table."""
    seed_all(db_session)
    scores = evaluate_and_store_anomalies(db_session, academic_year="2026-27")
    assert len(scores) > 0

    # Verify rows in DB
    db_records = list(
        db_session.scalars(
            select(AnomalyScore).where(AnomalyScore.academic_year == "2026-27")
        ).all()
    )
    assert len(db_records) >= len(scores)

    # Check that BNITS, Mysuru, Hubballi courses are flagged
    flagged_recs = [r for r in db_records if r.flagged]
    assert len(flagged_recs) >= 3

    # Check features_json structure
    sample = db_records[0]
    assert isinstance(sample.features_json, dict)
    assert "yoy_growth" in sample.features_json
    assert "nri_share" in sample.features_json
    assert "dob_cluster_ratio" in sample.features_json
    assert "max_apaar_sequence_run" in sample.features_json


# =============================================================================
# 9. API Endpoints & RBAC: GET /api/v1/analytics/anomalies
# =============================================================================

def test_get_anomalies_api_aicte(client: TestClient, db_session: Session):
    """AICTE officer successfully accesses /api/v1/analytics/anomalies."""
    seed_all(db_session)
    officer = db_session.scalar(select(User).where(User.email == "aicte_officer@aicte-india.org"))
    assert officer is not None
    token = create_access_token(user_id=officer.id, email=officer.email, role=officer.role)

    # Ensure anomalies are populated
    evaluate_and_store_anomalies(db_session, academic_year="2026-27")

    response = client.get(
        "/api/v1/analytics/anomalies?academic_year=2026-27",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "flagged_count" in data
    assert "items" in data
    assert data["total"] > 0

    # Test flagged_only filter
    flagged_resp = client.get(
        "/api/v1/analytics/anomalies?academic_year=2026-27&flagged_only=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert flagged_resp.status_code == 200
    flagged_data = flagged_resp.json()
    assert all(item["flagged"] is True for item in flagged_data["items"])


def test_get_anomalies_api_college_blocked(client: TestClient, db_session: Session):
    """College admin receives 403 Forbidden attempting to access AICTE anomaly analytics."""
    seed_all(db_session)
    college_admin = db_session.scalar(select(User).where(User.email == "admin@piaet-pune.edu.in"))
    assert college_admin is not None
    token = create_access_token(
        user_id=college_admin.id,
        email=college_admin.email,
        role=college_admin.role,
        institution_id=college_admin.institution_id,
    )

    response = client.get(
        "/api/v1/analytics/anomalies",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
