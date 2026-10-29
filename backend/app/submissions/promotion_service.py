"""Submission promotion to Central Repository, cross-college re-checks, and SSE dispatch."""

from __future__ import annotations

import logging
from typing import Any

import redis
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.analytics.anomaly_service import evaluate_and_store_anomalies
from app.analytics.sse import publish_sse_event
from app.models import (
    Notification,
    ReviewItem,
    SeatDeclaration,
    Student,
    Submission,
    User,
    ValidationFlag,
)
from app.students.duplicate_service import (
    DUP_ACTIVE_OTHER_COLLEGE,
    DUP_SAME_COURSE_OTHER_COLLEGE,
    are_courses_equivalent,
    notify_duplicate_enrolment,
    query_duplicates_by_apaar_and_year,
)
from app.submissions.state_machine import SubmissionState

logger = logging.getLogger(__name__)


def promote_submission_and_run_cross_checks(
    db: Session,
    submission: Submission,
    user: User,
    redis_client: redis.Redis | None = None,
    client_ip: str = "127.0.0.1",
) -> dict[str, Any]:
    """Execute complete post-submission lifecycle actions:
    - Promotes student records into central repository (status='submitted', is_locked=True)
    - Locks seat declarations
    - Runs cross-college duplicate checks across the entire database
    - Generates and persists duplicate flags for both sides
    - Sends notifications to all affected institutions
    - Creates AICTE review queue items for exception flags
    - Publishes real-time events via Server-Sent Events (SSE)
    """
    institution_id = submission.institution_id
    academic_year = submission.academic_year

    # 1. Promote and lock active student records
    students = list(
        db.scalars(
            select(Student)
            .options(joinedload(Student.course), joinedload(Student.institution))
            .where(
                Student.institution_id == institution_id,
                Student.academic_year == academic_year,
            )
        ).all()
    )

    regular_count = 0
    super_count = 0
    apaar_ids: list[str] = []

    for s in students:
        s.is_locked = True
        s.submission_id = submission.id
        if (s.status or "").lower() not in ("withdrawn", "transferred"):
            s.status = "submitted"
            if s.seat_type == "Regular":
                regular_count += 1
            elif s.seat_type == "Supernumerary":
                super_count += 1
            if s.apaar_id and len(str(s.apaar_id).strip()) == 12:
                apaar_ids.append(str(s.apaar_id).strip())

    # 2. Lock institutional seat declarations & link validation flags
    inst_course_ids = {s.course_id for s in students if s.course_id is not None}
    student_ids = [s.id for s in students]

    if student_ids:
        db.execute(
            update(ValidationFlag)
            .where(
                ValidationFlag.student_id.in_(student_ids),
                ValidationFlag.submission_id.is_(None),
            )
            .values(submission_id=submission.id)
        )
    if inst_course_ids:
        db.execute(
            update(ValidationFlag)
            .where(
                ValidationFlag.course_id.in_(inst_course_ids),
                ValidationFlag.submission_id.is_(None),
            )
            .values(submission_id=submission.id)
        )
    if inst_course_ids:
        inst_decls = list(
            db.scalars(
                select(SeatDeclaration).where(
                    SeatDeclaration.course_id.in_(inst_course_ids),
                    SeatDeclaration.academic_year == academic_year,
                )
            ).all()
        )
        for d in inst_decls:
            d.status = "locked"

    db.flush()

    # 3. Cross-college duplicate re-checks across all institutions
    duplicates_detected_count = 0
    notifications_dispatched_count = 0

    if apaar_ids:
        # Query active records at any other college matching these APAAR IDs
        other_students = query_duplicates_by_apaar_and_year(
            db=db,
            apaar_ids=apaar_ids,
            academic_year=academic_year,
            exclude_institution_id=institution_id,
        )

        if other_students:
            other_by_apaar: dict[str, list[Student]] = {}
            for os in other_students:
                if os.apaar_id:
                    other_by_apaar.setdefault(os.apaar_id, []).append(os)

            # Map submitting students by apaar_id
            submitting_by_apaar: dict[str, list[Student]] = {}
            for s in students:
                if (s.status or "").lower() not in ("withdrawn", "transferred") and s.apaar_id:
                    submitting_by_apaar.setdefault(s.apaar_id, []).append(s)

            for matched_apaar, conf_list in other_by_apaar.items():
                current_list = submitting_by_apaar.get(matched_apaar, [])
                if not current_list:
                    continue

                for cur_s in current_list:
                    for oth_s in conf_list:
                        duplicates_detected_count += 1

                        # Determine if same course or different course
                        has_same_course = are_courses_equivalent(cur_s.course, oth_s.course)
                        rule_code = (
                            DUP_SAME_COURSE_OTHER_COLLEGE
                            if has_same_course
                            else DUP_ACTIVE_OTHER_COLLEGE
                        )
                        rule_level = "exception" if has_same_course else "warning"
                        requires_just = has_same_course

                        inst_a = cur_s.institution
                        inst_b = oth_s.institution
                        name_a = inst_a.name if inst_a else f"Institution #{cur_s.institution_id}"
                        aicte_a = inst_a.aicte_id if inst_a else "AICTE-A"
                        name_b = inst_b.name if inst_b else f"Institution #{oth_s.institution_id}"
                        aicte_b = inst_b.aicte_id if inst_b else "AICTE-B"

                        # A. Ensure duplicate flag exists on submitting student
                        existing_flag_a = db.scalar(
                            select(ValidationFlag).where(
                                ValidationFlag.student_id == cur_s.id,
                                ValidationFlag.rule_code == rule_code,
                                ValidationFlag.status.in_(["open", "justified"]),
                            )
                        )
                        if not existing_flag_a:
                            flag_a = ValidationFlag(
                                student_id=cur_s.id,
                                course_id=cur_s.course_id,
                                submission_id=submission.id,
                                rule_code=rule_code,
                                level=rule_level,
                                field="apaar_id",
                                message=(
                                    f"APAAR ID {cur_s.apaar_id} is also active at {name_b} "
                                    f"({aicte_b}) for academic year {academic_year}."
                                ),
                                fix_hint=(
                                    "Verify student enrolment status with the other institution."
                                ),
                                audience="both",
                                requires_justification=requires_just,
                                status="open",
                            )
                            db.add(flag_a)

                        # B. Ensure duplicate flag exists on conflicting student
                        oth_sub_id = (
                            oth_s.submission_id
                            or (oth_s.submission.id if oth_s.submission else None)
                        )
                        existing_flag_b = db.scalar(
                            select(ValidationFlag).where(
                                ValidationFlag.student_id == oth_s.id,
                                ValidationFlag.rule_code == rule_code,
                                ValidationFlag.status.in_(["open", "justified"]),
                            )
                        )
                        if not existing_flag_b:
                            flag_b = ValidationFlag(
                                student_id=oth_s.id,
                                course_id=oth_s.course_id,
                                submission_id=oth_sub_id,
                                rule_code=rule_code,
                                level=rule_level,
                                field="apaar_id",
                                message=(
                                    f"APAAR ID {oth_s.apaar_id} is also active at {name_a} "
                                    f"({aicte_a}) for academic year {academic_year}."
                                ),
                                fix_hint=(
                                    "Verify student enrolment status with the other institution."
                                ),
                                audience="both",
                                requires_justification=requires_just,
                                status="open",
                            )
                            db.add(flag_b)
                            db.flush()

                            # If other institution already submitted and this is an exception,
                            # update other submission status and create review item
                            if (
                                oth_s.submission
                                and oth_s.submission.status == SubmissionState.SUBMITTED.value
                                and rule_level == "exception"
                            ):
                                oth_s.submission.status = (
                                    SubmissionState.SUBMITTED_WITH_EXCEPTIONS.value
                                )
                                rev_oth = ReviewItem(
                                    submission_id=oth_s.submission.id,
                                    flag_ids=[flag_b.id],
                                    status="pending",
                                )
                                db.add(rev_oth)
                                publish_sse_event(
                                    redis_client=redis_client,
                                    event_type="review_item_created",
                                    data={
                                        "review_item_id": rev_oth.id,
                                        "submission_id": oth_s.submission.id,
                                        "institution_id": oth_s.institution_id,
                                        "flag_ids": rev_oth.flag_ids,
                                        "status": rev_oth.status,
                                    },
                                )

                        # C. Notifications to affected colleges (deduplicated)
                        # Check if duplicate notification for this pair already exists
                        existing_notif = db.scalar(
                            select(Notification).where(
                                Notification.institution_id == cur_s.institution_id,
                                Notification.type == "DUPLICATE_ENROLMENT_DETECTED",
                            )
                        )
                        already_sent = False
                        if existing_notif and isinstance(existing_notif.payload_json, dict):
                            if (
                                existing_notif.payload_json.get("apaar_id") == cur_s.apaar_id
                                and existing_notif.payload_json.get("other_institution_id")
                                == oth_s.institution_id
                            ):
                                already_sent = True

                        if not already_sent:
                            notify_duplicate_enrolment(
                                db=db,
                                student=cur_s,
                                conflicting_student=oth_s,
                                rule_code=rule_code,
                            )
                            notifications_dispatched_count += 2

                        # D. Publish SSE event for duplicate detection
                        publish_sse_event(
                            redis_client=redis_client,
                            event_type="duplicate_enrolment_detected",
                            data={
                                "apaar_id": cur_s.apaar_id,
                                "rule_code": rule_code,
                                "level": rule_level,
                                "academic_year": academic_year,
                                "institutions": [
                                    {
                                        "institution_id": cur_s.institution_id,
                                        "name": name_a,
                                        "aicte_id": aicte_a,
                                        "course_id": cur_s.course_id,
                                    },
                                    {
                                        "institution_id": oth_s.institution_id,
                                        "name": name_b,
                                        "aicte_id": aicte_b,
                                        "course_id": oth_s.course_id,
                                    },
                                ],
                            },
                        )

    db.flush()

    # 4. Review items created for exceptions
    exception_flags = list(
        db.scalars(
            select(ValidationFlag).where(
                ValidationFlag.submission_id == submission.id,
                ValidationFlag.level == "exception",
                ValidationFlag.status.in_(["open", "justified"]),
            )
        ).all()
    )

    # Check existing review items for this submission to avoid duplicate entries
    existing_items = list(
        db.scalars(
            select(ReviewItem).where(ReviewItem.submission_id == submission.id)
        ).all()
    )
    existing_flag_ids: set[int] = set()
    for item in existing_items:
        if isinstance(item.flag_ids, list):
            for fid in item.flag_ids:
                if isinstance(fid, int):
                    existing_flag_ids.add(fid)

    review_items_created_count = 0
    for fl in exception_flags:
        if fl.id not in existing_flag_ids:
            review_item = ReviewItem(
                submission_id=submission.id,
                flag_ids=[fl.id],
                status="pending",
            )
            db.add(review_item)
            db.flush()
            review_items_created_count += 1
            existing_flag_ids.add(fl.id)

            publish_sse_event(
                redis_client=redis_client,
                event_type="review_item_created",
                data={
                    "review_item_id": review_item.id,
                    "submission_id": submission.id,
                    "institution_id": institution_id,
                    "flag_ids": review_item.flag_ids,
                    "status": review_item.status,
                },
            )

    # Ensure submission state is submitted_with_exceptions if exceptions exist
    if exception_flags:
        submission.status = SubmissionState.SUBMITTED_WITH_EXCEPTIONS.value
    else:
        submission.status = SubmissionState.SUBMITTED.value

    # 4b. Issue verified records on clean submission (SPEC.md Section 14, TASKS.md T32)
    verified_records_issued = 0
    if not exception_flags:
        from app.verification.service import issue_verified_records_for_submission

        issued_records = issue_verified_records_for_submission(
            db=db,
            submission=submission,
            actor=user,
            client_ip=client_ip,
        )
        verified_records_issued = len(issued_records)

    # 5. Publish SSE event for successful submission promotion
    inst_name = (
        submission.institution.name
        if submission.institution
        else f"Institution #{institution_id}"
    )
    inst_aicte_id = submission.institution.aicte_id if submission.institution else "AICTE-ID"

    publish_sse_event(
        redis_client=redis_client,
        event_type="submission_submitted",
        data={
            "submission_id": submission.id,
            "institution_id": institution_id,
            "institution_name": inst_name,
            "aicte_id": inst_aicte_id,
            "academic_year": academic_year,
            "status": submission.status,
            "receipt_no": submission.receipt_no,
            "total_students": len(students),
            "regular_students": regular_count,
            "supernumerary_students": super_count,
            "exceptions_count": len(exception_flags),
            "submitted_at": (
                submission.submitted_at.isoformat()
                if submission.submitted_at
                else ""
            ),
        },
    )

    db.flush()

    # 7. Evaluate and persist multi-dimensional anomaly detection scores
    anomalies_flagged_count = 0
    try:
        anomaly_scores = evaluate_and_store_anomalies(db=db, academic_year=academic_year)
        inst_anomalies = [
            a for a in anomaly_scores if a.institution_id == institution_id and a.flagged
        ]
        anomalies_flagged_count = len(inst_anomalies)
        if inst_anomalies:
            publish_sse_event(
                redis_client=redis_client,
                event_type="anomaly_detected",
                data={
                    "institution_id": institution_id,
                    "institution_name": inst_name,
                    "aicte_id": inst_aicte_id,
                    "academic_year": academic_year,
                    "flagged_courses_count": len(inst_anomalies),
                    "anomalies": [
                        {
                            "course_id": a.course_id,
                            "score": a.score,
                            "summary": (a.features_json or {}).get("summary"),
                        }
                        for a in inst_anomalies
                    ],
                },
            )
    except Exception as exc:
        logger.warning("Anomaly evaluation on submission promotion skipped: %s", exc)

    return {
        "status": submission.status,
        "receipt_no": submission.receipt_no,
        "total_students": len(students),
        "regular_students": regular_count,
        "supernumerary_students": super_count,
        "duplicates_detected": duplicates_detected_count,
        "notifications_dispatched": notifications_dispatched_count,
        "review_items_created": review_items_created_count,
        "verified_records_issued": verified_records_issued,
        "exception_flags_count": len(exception_flags),
        "anomalies_flagged_count": anomalies_flagged_count,
    }
