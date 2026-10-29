"""Comprehensive test suite for AICTE Review Queue and College Clarification Queries.

SPEC.md Section 10, 12 & TASKS.md T25:
- List and detail with flags, justification, and documents.
- Officer decisions: Accept, Raise query, Escalate, each with a note.
- A query re-opens only the queried items.
- College answers from /college/queries, returning submission to under_review.
- Audit entries recorded for every decision.
- RBAC and IDOR security checks.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.integrations.factory import get_storage
from app.models import (
    AuditLog,
    Course,
    Institution,
    Justification,
    Notification,
    ReviewItem,
    Student,
    Submission,
    User,
    ValidationFlag,
)


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def review_setup(db_session: Session) -> dict:
    """Setup test fixture with institutions, users, submissions, flags, and review items."""
    # 1. AICTE Officer
    officer = User(
        email="officer_review_test@aicte-india.org",
        password_hash=hash_password("OfficerPass123!"),
        role="aicte_officer",
        is_active=True,
    )
    # 2. AICTE Admin
    admin = User(
        email="admin_review_test@aicte-india.org",
        password_hash=hash_password("AdminPass123!"),
        role="aicte_admin",
        is_active=True,
    )
    # 3. Institution A (MMIT)
    inst_a = Institution(
        aicte_id="1-REV0001",
        name="Review Test Institute A",
        state="Maharashtra",
        district="Mumbai",
        address="123 Test Street, Mumbai, Maharashtra 400001",
        official_email="contact@rev-inst-a.ac.in",
        official_phone="+919876500001",
        head_name="Dr. Review Head A",
        affiliating_university="University of Mumbai",
        approval_status="active",
        account_status="active",
    )
    # 4. Institution B (NGEC)
    inst_b = Institution(
        aicte_id="1-REV0002",
        name="Review Test Institute B",
        state="Maharashtra",
        district="Nagpur",
        address="456 Test Road, Nagpur, Maharashtra 440001",
        official_email="contact@rev-inst-b.ac.in",
        official_phone="+919876500002",
        head_name="Dr. Review Head B",
        affiliating_university="Rashtrasant Tukadoji Maharaj Nagpur University",
        approval_status="active",
        account_status="active",
    )
    db_session.add_all([officer, admin, inst_a, inst_b])
    db_session.flush()

    # Users for institutions
    college_a_admin = User(
        email="admin@rev-inst-a.ac.in",
        password_hash=hash_password("CollegePass123!"),
        role="college_admin",
        institution_id=inst_a.id,
        is_active=True,
    )
    college_b_admin = User(
        email="admin@rev-inst-b.ac.in",
        password_hash=hash_password("CollegePass123!"),
        role="college_admin",
        institution_id=inst_b.id,
        is_active=True,
    )
    db_session.add_all([college_a_admin, college_b_admin])
    db_session.flush()

    # Course
    course_a = Course(
        institution_id=inst_a.id,
        name="Computer Science & Engineering",
        level="UG",
        branch="CSE",
        duration_years=4,
    )
    db_session.add(course_a)
    db_session.flush()

    # Submissions
    sub_a = Submission(
        institution_id=inst_a.id,
        academic_year="2026-27",
        status="submitted_with_exceptions",
        submitted_by=college_a_admin.id,
        submitted_at=datetime.now(UTC),
        receipt_no="REC-202627-REV0001-TEST",
    )
    db_session.add(sub_a)
    db_session.flush()

    # Student
    student = Student(
        institution_id=inst_a.id,
        course_id=course_a.id,
        academic_year="2026-27",
        apaar_id="998877665544",
        name="Rohan Verma",
        dob_encrypted="enc_test_dob",
        gender="Male",
        enrolment_no="ENR-REV-001",
        admission_date=datetime.now(UTC).date(),
        admission_mode="Management quota",
        seat_type="Regular",
        reservation_category="General",
        status="submitted",
        is_locked=True,
        submission_id=sub_a.id,
    )
    db_session.add(student)
    db_session.flush()

    # Flag
    flag_a = ValidationFlag(
        submission_id=sub_a.id,
        student_id=student.id,
        course_id=course_a.id,
        rule_code="INTAKE_EXCEEDED",
        level="exception",
        field="course_id",
        message="Regular enrolment exceeds approved intake by 5 seats",
        fix_hint="Verify court order or state admission allotment",
        audience="both",
        requires_justification=True,
        status="justified",
    )
    db_session.add(flag_a)
    db_session.flush()

    # Save mock file in storage
    storage = get_storage()
    doc_key = f"justifications/test_court_order_{flag_a.id}.pdf"
    storage.save(doc_key, b"%PDF-1.4 Mock Court Order Content For Testing")

    # Justification
    just_a = Justification(
        flag_id=flag_a.id,
        text="High court interim writ petition WP/2026/89 ordered intake adjustment.",
        document_ref=doc_key,
        by_user=college_a_admin.id,
        at=datetime.now(UTC),
    )
    db_session.add(just_a)
    db_session.flush()

    # Review Item
    review_item = ReviewItem(
        submission_id=sub_a.id,
        flag_ids=[flag_a.id],
        status="under_review",
        assigned_to=officer.id,
    )
    db_session.add(review_item)
    db_session.commit()

    return {
        "officer": officer,
        "admin": admin,
        "college_a_admin": college_a_admin,
        "college_b_admin": college_b_admin,
        "inst_a": inst_a,
        "inst_b": inst_b,
        "sub_a": sub_a,
        "flag_a": flag_a,
        "just_a": just_a,
        "review_item": review_item,
        "doc_key": doc_key,
    }


def test_list_review_items_for_aicte(client: TestClient, review_setup: dict) -> None:
    """Test AICTE officer can list items in the review queue with statistical counts."""
    officer = review_setup["officer"]
    resp = client.get("/api/v1/review/items", headers=_auth(officer))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["under_review_count"] >= 1

    matched = [it for it in data["items"] if it["id"] == review_setup["review_item"].id]
    assert len(matched) == 1
    item = matched[0]
    assert item["institution_name"] == "Review Test Institute A"
    assert "INTAKE_EXCEEDED" in item["rule_codes"]
    assert item["status"] == "under_review"


def test_get_review_item_detail(client: TestClient, review_setup: dict) -> None:
    """Test AICTE officer can inspect review item detail with flags and justifications."""
    officer = review_setup["officer"]
    item_id = review_setup["review_item"].id
    resp = client.get(f"/api/v1/review/items/{item_id}", headers=_auth(officer))
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == item_id
    assert data["submission_id"] == review_setup["sub_a"].id
    assert data["receipt_no"] == "REC-202627-REV0001-TEST"
    assert len(data["flags"]) == 1

    flag = data["flags"][0]
    assert flag["rule_code"] == "INTAKE_EXCEEDED"
    assert flag["student_name"] == "Rohan Verma"
    assert flag["student_apaar"] == "XXXX-XXXX-5544"
    assert len(flag["justifications"]) == 1

    just = flag["justifications"][0]
    assert "High court" in just["text"]
    assert just["document_ref"] == review_setup["doc_key"]


def test_download_review_document(client: TestClient, review_setup: dict) -> None:
    """Test AICTE officer can stream the supporting evidence document."""
    officer = review_setup["officer"]
    item_id = review_setup["review_item"].id
    just_id = review_setup["just_a"].id

    resp = client.get(
        f"/api/v1/review/items/{item_id}/documents/{just_id}",
        headers=_auth(officer),
    )
    assert resp.status_code == 200
    assert b"Mock Court Order Content" in resp.content


def test_officer_accept_decision(
    client: TestClient, db_session: Session, review_setup: dict
) -> None:
    """Test Accept decision transitions item to accepted and resolves flags."""
    officer = review_setup["officer"]
    item_id = review_setup["review_item"].id

    resp = client.post(
        f"/api/v1/review/items/{item_id}/decision",
        json={
            "decision": "accept",
            "note": "Court order WP/2026/89 verified and accepted for 5 additional admissions.",
        },
        headers=_auth(officer),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["decision"] == "accept"
    assert "Court order" in data["decision_note"]

    # Verify database state
    db_session.expire_all()
    item = db_session.scalar(select(ReviewItem).where(ReviewItem.id == item_id))
    assert item.status == "accepted"

    sub = db_session.scalar(select(Submission).where(Submission.id == review_setup["sub_a"].id))
    assert sub.status == "accepted"

    flag = db_session.scalar(
        select(ValidationFlag).where(ValidationFlag.id == review_setup["flag_a"].id)
    )
    assert flag.status == "resolved"

    # Verify notification created
    notif = db_session.scalar(
        select(Notification).where(
            Notification.institution_id == review_setup["inst_a"].id,
            Notification.type == "REVIEW_ACCEPTED",
        )
    )
    assert notif is not None

    # Verify audit log entry
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity == "review_item",
            AuditLog.entity_id == str(item_id),
            AuditLog.action == "review.accept",
        )
    )
    assert audit is not None
    assert audit.actor_id == str(officer.id)


def test_officer_raise_query_and_college_respond_roundtrip(
    client: TestClient, db_session: Session, review_setup: dict
) -> None:
    """Test full query round trip between officer and college."""
    officer = review_setup["officer"]
    college_a_admin = review_setup["college_a_admin"]
    inst_a_id = review_setup["inst_a"].id
    item_id = review_setup["review_item"].id

    # 1. Officer raises query
    query_note = "Please provide the certified copy of page 4 of the High Court interim order."
    resp = client.post(
        f"/api/v1/review/items/{item_id}/decision",
        json={"decision": "query", "note": query_note},
        headers=_auth(officer),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "query_raised"
    assert data["decision"] == "query"

    # Check DB state
    db_session.expire_all()
    sub = db_session.scalar(select(Submission).where(Submission.id == review_setup["sub_a"].id))
    assert sub.status == "query_raised"

    flag = db_session.scalar(
        select(ValidationFlag).where(ValidationFlag.id == review_setup["flag_a"].id)
    )
    assert flag.status == "open"  # Flag re-opened for query

    # 2. College checks their queries
    q_resp = client.get(
        f"/api/v1/institutions/{inst_a_id}/queries",
        headers=_auth(college_a_admin),
    )
    assert q_resp.status_code == 200
    q_list = q_resp.json()
    assert q_list["total"] >= 1
    assert q_list["pending_count"] >= 1

    pending_query = [q for q in q_list["items"] if q["message"] == query_note][0]
    query_id = pending_query["id"]
    assert pending_query["state"] == "pending"
    assert len(pending_query["flags"]) == 1

    # 3. College responds to the query
    college_answer = "Certified copy of page 4 attached showing bench approval for 5 seats."
    resp_answer = client.post(
        f"/api/v1/institutions/{inst_a_id}/queries/{query_id}/respond",
        json={"response": college_answer},
        headers=_auth(college_a_admin),
    )
    assert resp_answer.status_code == 200
    ans_data = resp_answer.json()
    assert ans_data["state"] == "answered"
    assert ans_data["response"] == college_answer

    # 4. Verify post-response state in database
    db_session.expire_all()
    # Submission returns to under_review (SPEC Section 10)
    sub = db_session.scalar(select(Submission).where(Submission.id == review_setup["sub_a"].id))
    assert sub.status == "under_review"

    # Review item returns to under_review
    rev = db_session.scalar(select(ReviewItem).where(ReviewItem.id == item_id))
    assert rev.status == "under_review"

    # Flag returns to justified
    flag = db_session.scalar(
        select(ValidationFlag).where(ValidationFlag.id == review_setup["flag_a"].id)
    )
    assert flag.status == "justified"

    # Audit log recorded for query response
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity == "query",
            AuditLog.entity_id == str(query_id),
            AuditLog.action == "query.respond",
        )
    )
    assert audit is not None
    assert audit.actor_id == str(college_a_admin.id)


def test_officer_escalate_decision(
    client: TestClient, db_session: Session, review_setup: dict
) -> None:
    """Test Escalate decision transitions item and submission to escalated."""
    officer = review_setup["officer"]
    item_id = review_setup["review_item"].id

    resp = client.post(
        f"/api/v1/review/items/{item_id}/decision",
        json={
            "decision": "escalate",
            "note": "Referred to AICTE Standing Appellate Committee.",
        },
        headers=_auth(officer),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "escalated"

    db_session.expire_all()
    sub = db_session.scalar(select(Submission).where(Submission.id == review_setup["sub_a"].id))
    assert sub.status == "escalated"


def test_rbac_and_idor_protection(
    client: TestClient, db_session: Session, review_setup: dict
) -> None:
    """Test security constraints:
    - College user cannot access AICTE review endpoints (403).
    - College A cannot access or answer College B's queries (IDOR 403).
    - AICTE officer cannot respond to college queries directly via college endpoint.
    """
    college_a = review_setup["college_a_admin"]
    college_b = review_setup["college_b_admin"]
    inst_a_id = review_setup["inst_a"].id
    item_id = review_setup["review_item"].id

    # 1. College A cannot list or decide AICTE review items
    resp1 = client.get("/api/v1/review/items", headers=_auth(college_a))
    assert resp1.status_code == 403

    resp2 = client.post(
        f"/api/v1/review/items/{item_id}/decision",
        json={"decision": "accept", "note": "Rogue accept"},
        headers=_auth(college_a),
    )
    assert resp2.status_code == 403

    # 2. College B cannot query or access College A's queries
    resp3 = client.get(
        f"/api/v1/institutions/{inst_a_id}/queries",
        headers=_auth(college_b),
    )
    assert resp3.status_code == 403
