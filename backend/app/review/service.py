"""Business logic and database operations for AICTE Review Queue and College Queries."""

from __future__ import annotations

import mimetypes
import uuid
from datetime import UTC, datetime
from pathlib import Path

import redis
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.analytics.sse import publish_sse_event
from app.audit import service as audit_service
from app.integrations.factory import get_storage
from app.models import (
    Institution,
    Justification,
    Notification,
    Query,
    ReviewItem,
    Submission,
    User,
    ValidationFlag,
)
from app.review.schemas import (
    CollegeQueryListResponse,
    CollegeQueryResponse,
    QueryItemResponse,
    ReviewFlagDetail,
    ReviewItemDetailResponse,
    ReviewItemListResponse,
    ReviewItemSummary,
    ReviewJustificationDetail,
)
from app.submissions.state_machine import SubmissionState, SubmissionStateMachine


def list_review_items(
    db: Session,
    status_filter: str | None = None,
    academic_year: str | None = None,
    institution_id: int | None = None,
    search: str | None = None,
) -> ReviewItemListResponse:
    """Retrieve review items for the AICTE officer queue with counts and summaries."""
    # Build query
    query = (
        select(ReviewItem)
        .join(Submission, ReviewItem.submission_id == Submission.id)
        .join(Institution, Submission.institution_id == Institution.id)
        .options(
            joinedload(ReviewItem.submission).joinedload(Submission.institution),
            joinedload(ReviewItem.assignee),
            selectinload(ReviewItem.queries),
        )
        .order_by(ReviewItem.created_at.desc())
    )

    if academic_year:
        query = query.where(Submission.academic_year == academic_year)
    if institution_id:
        query = query.where(Submission.institution_id == institution_id)
    if status_filter:
        query = query.where(ReviewItem.status == status_filter)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Institution.name.ilike(search_term),
                Institution.aicte_id.ilike(search_term),
                Institution.state.ilike(search_term),
                Submission.receipt_no.ilike(search_term),
            )
        )

    all_items = db.scalars(query).unique().all()

    # Collect all flag IDs to batch-fetch rule codes
    all_flag_ids: set[int] = set()
    for item in all_items:
        if isinstance(item.flag_ids, list):
            for fid in item.flag_ids:
                if isinstance(fid, int):
                    all_flag_ids.add(fid)

    flags_by_id: dict[int, ValidationFlag] = {}
    if all_flag_ids:
        flag_records = db.scalars(
            select(ValidationFlag).where(ValidationFlag.id.in_(all_flag_ids))
        ).all()
        flags_by_id = {fl.id: fl for fl in flag_records}

    # Statistical counts across all review items
    count_stmt = select(ReviewItem.status, func.count(ReviewItem.id)).group_by(ReviewItem.status)
    if academic_year:
        count_stmt = count_stmt.join(Submission).where(Submission.academic_year == academic_year)
    counts_map = dict(db.execute(count_stmt).all())

    summaries: list[ReviewItemSummary] = []
    for item in all_items:
        item_flag_ids = [fid for fid in item.flag_ids if isinstance(fid, int)]
        item_rule_codes = list(
            {flags_by_id[fid].rule_code for fid in item_flag_ids if fid in flags_by_id}
        )
        pending_queries = sum(1 for q in item.queries if q.state == "pending")

        inst = item.submission.institution
        summaries.append(
            ReviewItemSummary(
                id=item.id,
                submission_id=item.submission_id,
                institution_id=inst.id,
                institution_name=inst.name,
                aicte_id=inst.aicte_id,
                state=inst.state,
                academic_year=item.submission.academic_year,
                receipt_no=item.submission.receipt_no,
                status=item.status,
                decision=item.decision,
                decision_note=item.decision_note,
                decided_at=item.decided_at.isoformat() if item.decided_at else None,
                assigned_to=item.assigned_to,
                assigned_to_email=item.assignee.email if item.assignee else None,
                flag_ids=item_flag_ids,
                rule_codes=item_rule_codes,
                flag_count=len(item_flag_ids),
                pending_queries_count=pending_queries,
                created_at=item.created_at.isoformat(),
                updated_at=item.updated_at.isoformat(),
            )
        )

    return ReviewItemListResponse(
        total=len(summaries),
        pending_count=counts_map.get("pending", 0),
        under_review_count=counts_map.get("under_review", 0),
        queries_raised_count=counts_map.get("query_raised", 0),
        escalated_count=counts_map.get("escalated", 0),
        accepted_count=counts_map.get("accepted", 0),
        items=summaries,
    )


def get_review_item_detail(db: Session, review_item_id: int) -> ReviewItemDetailResponse:
    """Retrieve complete context for a review item including flags, student rows, and queries."""
    item = db.scalar(
        select(ReviewItem)
        .where(ReviewItem.id == review_item_id)
        .options(
            joinedload(ReviewItem.submission).joinedload(Submission.institution),
            joinedload(ReviewItem.assignee),
            selectinload(ReviewItem.queries),
        )
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item {review_item_id} not found.",
        )

    # Load associated flags
    flag_ids = [fid for fid in item.flag_ids if isinstance(fid, int)]
    flag_details: list[ReviewFlagDetail] = []

    if flag_ids:
        flags = db.scalars(
            select(ValidationFlag)
            .where(ValidationFlag.id.in_(flag_ids))
            .options(
                joinedload(ValidationFlag.justifications).joinedload(Justification.author),
                joinedload(ValidationFlag.student),
                joinedload(ValidationFlag.course),
            )
        ).unique().all()

        for fl in flags:
            just_details = [
                ReviewJustificationDetail(
                    id=j.id,
                    flag_id=j.flag_id,
                    text=j.text,
                    document_ref=j.document_ref,
                    document_filename=Path(j.document_ref).name if j.document_ref else None,
                    by_user_id=j.by_user,
                    by_user_email=j.author.email if j.author else None,
                    at=j.at.isoformat(),
                )
                for j in fl.justifications
            ]

            masked_apaar = None
            if fl.student and fl.student.apaar_id:
                raw_id = fl.student.apaar_id
                masked_apaar = f"XXXX-XXXX-{raw_id[-4:]}" if len(raw_id) == 12 else raw_id

            flag_details.append(
                ReviewFlagDetail(
                    id=fl.id,
                    submission_id=fl.submission_id,
                    rule_code=fl.rule_code,
                    level=fl.level,
                    field=fl.field,
                    row_ref=str(fl.student_id) if fl.student_id else None,
                    message=fl.message,
                    fix_hint=fl.fix_hint,
                    status=fl.status,
                    student_id=fl.student_id,
                    student_name=fl.student.name if fl.student else None,
                    student_apaar=masked_apaar,
                    course_id=fl.course_id,
                    course_name=fl.course.name if fl.course else None,
                    branch=fl.course.branch if fl.course else None,
                    justifications=just_details,
                )
            )

    # Sort queries chronologically
    sorted_queries = sorted(item.queries, key=lambda q: q.created_at)
    query_details: list[QueryItemResponse] = []
    for q in sorted_queries:
        # Load user emails if needed
        creator = db.scalar(select(User).where(User.id == q.created_by)) if q.created_by else None
        responder = (
            db.scalar(select(User).where(User.id == q.responded_by)) if q.responded_by else None
        )
        query_details.append(
            QueryItemResponse(
                id=q.id,
                review_item_id=q.review_item_id,
                submission_id=q.submission_id,
                message=q.message,
                response=q.response,
                state=q.state,
                created_by=q.created_by,
                created_by_email=creator.email if creator else None,
                responded_by=q.responded_by,
                responded_by_email=responder.email if responder else None,
                created_at=q.created_at.isoformat(),
                responded_at=q.responded_at.isoformat() if q.responded_at else None,
            )
        )

    inst = item.submission.institution
    return ReviewItemDetailResponse(
        id=item.id,
        submission_id=item.submission_id,
        institution_id=inst.id,
        institution_name=inst.name,
        aicte_id=inst.aicte_id,
        state=inst.state,
        district=inst.district,
        academic_year=item.submission.academic_year,
        submission_status=item.submission.status,
        receipt_no=item.submission.receipt_no,
        submitted_at=item.submission.submitted_at.isoformat()
        if item.submission.submitted_at
        else None,
        status=item.status,
        decision=item.decision,
        decision_note=item.decision_note,
        decided_at=item.decided_at.isoformat() if item.decided_at else None,
        assigned_to=item.assigned_to,
        assigned_to_email=item.assignee.email if item.assignee else None,
        flags=flag_details,
        queries=query_details,
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
    )


def decide_review_item(
    db: Session,
    review_item_id: int,
    user: User,
    decision: str,
    note: str,
    redis_client: redis.Redis | None = None,
    client_ip: str = "127.0.0.1",
) -> ReviewItemDetailResponse:
    """Record an AICTE officer's review decision (accept, query, escalate).

    - Accept: marks item accepted, resolves flags, auto-accepts submission if all items clear.
    - Query: creates Query record, re-opens queried items, moves submission to query_raised.
    - Escalate: marks item escalated, notifies higher authority.
    - Writes immutable audit log entry (Hard Rule 6).
    """
    item = db.scalar(
        select(ReviewItem)
        .where(ReviewItem.id == review_item_id)
        .options(
            joinedload(ReviewItem.submission).joinedload(Submission.institution),
            joinedload(ReviewItem.assignee),
        )
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item {review_item_id} not found.",
        )

    clean_note = note.strip()
    if len(clean_note) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision note must be at least 3 characters long.",
        )

    now = datetime.now(UTC)
    prev_status = item.status
    submission = item.submission
    institution = submission.institution
    flag_ids = [fid for fid in item.flag_ids if isinstance(fid, int)]

    if decision == "accept":
        item.status = "accepted"
        item.decision = "accept"
        item.decision_note = clean_note
        item.decided_at = now
        item.assigned_to = user.id

        # Update associated flags: mark justified/resolved
        if flag_ids:
            flags = db.scalars(
                select(ValidationFlag).where(ValidationFlag.id.in_(flag_ids))
            ).all()
            for fl in flags:
                fl.status = "resolved"

        # Check if all other review items for this submission are accepted
        sibling_items = db.scalars(
            select(ReviewItem).where(
                ReviewItem.submission_id == submission.id,
                ReviewItem.id != item.id,
            )
        ).all()
        all_siblings_accepted = all(sib.status == "accepted" for sib in sibling_items)

        if all_siblings_accepted:
            if SubmissionStateMachine.can_transition(submission.status, SubmissionState.ACCEPTED):
                submission.status = SubmissionState.ACCEPTED.value
            else:
                submission.status = SubmissionState.ACCEPTED.value

            from app.verification.service import issue_verified_records_for_submission

            issue_verified_records_for_submission(
                db=db,
                submission=submission,
                actor=user,
                client_ip=client_ip,
            )
        else:
            # Issue verified record for student(s) whose flags were accepted
            from app.verification.service import issue_verified_record

            if flag_ids:
                accepted_flags = list(
                    db.scalars(
                        select(ValidationFlag)
                        .options(joinedload(ValidationFlag.student))
                        .where(ValidationFlag.id.in_(flag_ids))
                    ).all()
                )
                processed_students: set[int] = set()
                for fl in accepted_flags:
                    if fl.student and fl.student.id not in processed_students:
                        other_open = db.scalar(
                            select(ValidationFlag.id)
                            .where(
                                ValidationFlag.student_id == fl.student.id,
                                ValidationFlag.status == "open",
                            )
                            .limit(1)
                        )
                        if not other_open:
                            issue_verified_record(
                                db=db,
                                student=fl.student,
                                status_override="verified_with_exception",
                                actor=user,
                                client_ip=client_ip,
                            )
                            processed_students.add(fl.student.id)

        # Notification to college
        notif = Notification(
            institution_id=institution.id,
            type="REVIEW_ACCEPTED",
            payload_json={
                "review_item_id": item.id,
                "submission_id": submission.id,
                "academic_year": submission.academic_year,
                "receipt_no": submission.receipt_no,
                "officer_note": clean_note,
            },
        )
        db.add(notif)
        db.flush()

        # Audit log
        audit_service.record(
            db=db,
            actor_id=user.id,
            actor_role=user.role,
            action="review.accept",
            entity="review_item",
            entity_id=item.id,
            before_json={"status": prev_status, "decision": item.decision},
            after_json={
                "status": "accepted",
                "decision": "accept",
                "decision_note": clean_note,
                "decided_at": now.isoformat(),
                "assigned_to": user.id,
                "all_accepted": all_siblings_accepted,
            },
            ip=client_ip,
        )

        publish_sse_event(
            redis_client=redis_client,
            event_type="review_item_accepted",
            data={
                "review_item_id": item.id,
                "submission_id": submission.id,
                "institution_id": institution.id,
                "status": "accepted",
                "all_accepted": all_siblings_accepted,
            },
        )

    elif decision == "query":
        item.status = "query_raised"
        item.decision = "query"
        item.decision_note = clean_note
        item.decided_at = now
        item.assigned_to = user.id

        # Re-open only the queried items
        if flag_ids:
            flags = db.scalars(
                select(ValidationFlag).where(ValidationFlag.id.in_(flag_ids))
            ).all()
            for fl in flags:
                fl.status = "open"

        # Create Query record
        query_record = Query(
            review_item_id=item.id,
            submission_id=submission.id,
            message=clean_note,
            state="pending",
            created_by=user.id,
        )
        db.add(query_record)

        # Transition submission to query_raised
        if SubmissionStateMachine.can_transition(
            submission.status, SubmissionState.QUERY_RAISED
        ):
            submission.status = SubmissionState.QUERY_RAISED.value
        else:
            submission.status = SubmissionState.QUERY_RAISED.value

        # Notification to college
        notif = Notification(
            institution_id=institution.id,
            type="REVIEW_QUERY_RAISED",
            payload_json={
                "review_item_id": item.id,
                "submission_id": submission.id,
                "academic_year": submission.academic_year,
                "receipt_no": submission.receipt_no,
                "query_message": clean_note,
            },
        )
        db.add(notif)
        db.flush()

        # Audit log
        audit_service.record(
            db=db,
            actor_id=user.id,
            actor_role=user.role,
            action="review.query_raised",
            entity="review_item",
            entity_id=item.id,
            before_json={"status": prev_status, "decision": item.decision},
            after_json={
                "status": "query_raised",
                "decision": "query",
                "decision_note": clean_note,
                "query_id": query_record.id,
                "decided_at": now.isoformat(),
                "assigned_to": user.id,
            },
            ip=client_ip,
        )

        publish_sse_event(
            redis_client=redis_client,
            event_type="review_query_raised",
            data={
                "review_item_id": item.id,
                "query_id": query_record.id,
                "submission_id": submission.id,
                "institution_id": institution.id,
                "message": clean_note,
            },
        )

    elif decision == "escalate":
        item.status = "escalated"
        item.decision = "escalate"
        item.decision_note = clean_note
        item.decided_at = now
        item.assigned_to = user.id

        if SubmissionStateMachine.can_transition(
            submission.status, SubmissionState.ESCALATED
        ):
            submission.status = SubmissionState.ESCALATED.value
        else:
            submission.status = SubmissionState.ESCALATED.value

        # Notification
        notif = Notification(
            institution_id=institution.id,
            type="REVIEW_ESCALATED",
            payload_json={
                "review_item_id": item.id,
                "submission_id": submission.id,
                "academic_year": submission.academic_year,
                "escalation_note": clean_note,
            },
        )
        db.add(notif)
        db.flush()

        # Audit log
        audit_service.record(
            db=db,
            actor_id=user.id,
            actor_role=user.role,
            action="review.escalate",
            entity="review_item",
            entity_id=item.id,
            before_json={"status": prev_status, "decision": item.decision},
            after_json={
                "status": "escalated",
                "decision": "escalate",
                "decision_note": clean_note,
                "decided_at": now.isoformat(),
                "assigned_to": user.id,
            },
            ip=client_ip,
        )

        publish_sse_event(
            redis_client=redis_client,
            event_type="review_item_escalated",
            data={
                "review_item_id": item.id,
                "submission_id": submission.id,
                "institution_id": institution.id,
                "note": clean_note,
            },
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{decision}'. Must be 'accept', 'query', or 'escalate'.",
        )

    db.commit()
    return get_review_item_detail(db=db, review_item_id=item.id)


def list_institution_queries(
    db: Session,
    institution_id: int,
    state_filter: str | None = None,
    academic_year: str | None = None,
) -> CollegeQueryListResponse:
    """Retrieve all queries issued by AICTE to a college."""
    query = (
        select(Query)
        .join(Submission, Query.submission_id == Submission.id)
        .join(Institution, Submission.institution_id == Institution.id)
        .where(Institution.id == institution_id)
        .options(
            joinedload(Query.submission).joinedload(Submission.institution),
            joinedload(Query.review_item),
        )
        .order_by(Query.created_at.desc())
    )

    if academic_year:
        query = query.where(Submission.academic_year == academic_year)
    if state_filter:
        query = query.where(Query.state == state_filter)

    query_records = db.scalars(query).unique().all()

    # Collect flags across these review items
    all_flag_ids: set[int] = set()
    for q in query_records:
        if q.review_item and isinstance(q.review_item.flag_ids, list):
            for fid in q.review_item.flag_ids:
                if isinstance(fid, int):
                    all_flag_ids.add(fid)

    flags_map: dict[int, ValidationFlag] = {}
    if all_flag_ids:
        flags = db.scalars(
            select(ValidationFlag)
            .where(ValidationFlag.id.in_(all_flag_ids))
            .options(
                joinedload(ValidationFlag.course),
                joinedload(ValidationFlag.student),
                joinedload(ValidationFlag.justifications),
            )
        ).unique().all()
        flags_map = {fl.id: fl for fl in flags}

    # Fetch creator names
    creator_ids = {q.created_by for q in query_records if q.created_by}
    creators_map: dict[int, User] = {}
    if creator_ids:
        creators = db.scalars(select(User).where(User.id.in_(creator_ids))).all()
        creators_map = {u.id: u for u in creators}

    pending_count = 0
    items: list[CollegeQueryResponse] = []
    for q in query_records:
        if q.state == "pending":
            pending_count += 1

        sub = q.submission
        inst = sub.institution
        officer = creators_map.get(q.created_by) if q.created_by else None

        flag_details: list[ReviewFlagDetail] = []
        if q.review_item and isinstance(q.review_item.flag_ids, list):
            for fid in q.review_item.flag_ids:
                if fid in flags_map:
                    fl = flags_map[fid]
                    flag_details.append(
                        ReviewFlagDetail(
                            id=fl.id,
                            submission_id=fl.submission_id,
                            rule_code=fl.rule_code,
                            level=fl.level,
                            field=fl.field,
                            row_ref=str(fl.student_id) if fl.student_id else None,
                            message=fl.message,
                            fix_hint=fl.fix_hint,
                            status=fl.status,
                            student_id=fl.student_id,
                            student_name=fl.student.name if fl.student else None,
                            course_id=fl.course_id,
                            course_name=fl.course.name if fl.course else None,
                            branch=fl.course.branch if fl.course else None,
                        )
                    )

        items.append(
            CollegeQueryResponse(
                id=q.id,
                review_item_id=q.review_item_id,
                submission_id=q.submission_id,
                institution_id=inst.id,
                institution_name=inst.name,
                academic_year=sub.academic_year,
                receipt_no=sub.receipt_no,
                message=q.message,
                response=q.response,
                state=q.state,
                created_at=q.created_at.isoformat(),
                responded_at=q.responded_at.isoformat() if q.responded_at else None,
                officer_name=officer.email if officer else "AICTE Officer",
                flags=flag_details,
            )
        )

    return CollegeQueryListResponse(
        total=len(items),
        pending_count=pending_count,
        items=items,
    )


def get_institution_query_detail(
    db: Session,
    institution_id: int,
    query_id: int,
) -> CollegeQueryResponse:
    """Retrieve detailed query context for a college response."""
    query = db.scalar(
        select(Query)
        .where(Query.id == query_id)
        .options(
            joinedload(Query.submission).joinedload(Submission.institution),
            joinedload(Query.review_item),
        )
    )
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query {query_id} not found.",
        )

    if query.submission.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Query does not belong to your institution.",
        )

    sub = query.submission
    inst = sub.institution
    officer = (
        db.scalar(select(User).where(User.id == query.created_by)) if query.created_by else None
    )

    flag_details: list[ReviewFlagDetail] = []
    if query.review_item and isinstance(query.review_item.flag_ids, list):
        fids = [fid for fid in query.review_item.flag_ids if isinstance(fid, int)]
        if fids:
            flags = db.scalars(
                select(ValidationFlag)
                .where(ValidationFlag.id.in_(fids))
                .options(
                    joinedload(ValidationFlag.course),
                    joinedload(ValidationFlag.student),
                    joinedload(ValidationFlag.justifications),
                )
            ).unique().all()
            for fl in flags:
                flag_details.append(
                    ReviewFlagDetail(
                        id=fl.id,
                        submission_id=fl.submission_id,
                        rule_code=fl.rule_code,
                        level=fl.level,
                        field=fl.field,
                        row_ref=str(fl.student_id) if fl.student_id else None,
                        message=fl.message,
                        fix_hint=fl.fix_hint,
                        status=fl.status,
                        student_id=fl.student_id,
                        student_name=fl.student.name if fl.student else None,
                        course_id=fl.course_id,
                        course_name=fl.course.name if fl.course else None,
                        branch=fl.course.branch if fl.course else None,
                    )
                )

    return CollegeQueryResponse(
        id=query.id,
        review_item_id=query.review_item_id,
        submission_id=query.submission_id,
        institution_id=inst.id,
        institution_name=inst.name,
        academic_year=sub.academic_year,
        receipt_no=sub.receipt_no,
        message=query.message,
        response=query.response,
        state=query.state,
        created_at=query.created_at.isoformat(),
        responded_at=query.responded_at.isoformat() if query.responded_at else None,
        officer_name=officer.email if officer else "AICTE Officer",
        flags=flag_details,
    )


async def respond_to_query(
    db: Session,
    institution_id: int,
    query_id: int,
    user: User,
    response_text: str,
    document_ref: str | None = None,
    document_file: UploadFile | None = None,
    redis_client: redis.Redis | None = None,
    client_ip: str = "127.0.0.1",
) -> CollegeQueryResponse:
    """Submit a college response to an AICTE clarification inquiry.

    - Updates Query: response, state='answered', responded_by, responded_at.
    - Associated ReviewItem returns to status='under_review'.
    - Associated Submission returns to status='under_review' (SPEC Section 10).
    - Re-justifies flags if document or new justification provided.
    - Appends hash-chained audit log entry.
    """
    query = db.scalar(
        select(Query)
        .where(Query.id == query_id)
        .options(
            joinedload(Query.submission).joinedload(Submission.institution),
            joinedload(Query.review_item),
        )
    )
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query {query_id} not found.",
        )

    if query.submission.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Query does not belong to your institution.",
        )

    if query.state != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query {query_id} is in '{query.state}'. Only pending queries can be answered.",
        )

    clean_resp = response_text.strip()
    if len(clean_resp) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Response text must be at least 5 characters long.",
        )

    final_doc_ref = document_ref
    if document_file:
        file_bytes = await document_file.read()
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploaded document exceeds 10MB limit.",
            )
        filename = document_file.filename or "clarification_doc.pdf"
        storage = get_storage()
        f_hex = uuid.uuid4().hex[:8]
        doc_key = f"clarifications/inst_{institution_id}_q_{query_id}_{f_hex}_{filename}"
        final_doc_ref = storage.save(doc_key, file_bytes)

    now = datetime.now(UTC)
    query.response = clean_resp
    query.state = "answered"
    query.responded_by = user.id
    query.responded_at = now

    sub = query.submission
    # Return review item to under_review
    if query.review_item:
        query.review_item.status = "under_review"

        # If flags were opened by the query, mark them justified with this response
        if isinstance(query.review_item.flag_ids, list):
            fids = [fid for fid in query.review_item.flag_ids if isinstance(fid, int)]
            flags = db.scalars(select(ValidationFlag).where(ValidationFlag.id.in_(fids))).all()
            for fl in flags:
                fl.status = "justified"
                # Add clarification justification
                clarification_just = Justification(
                    flag_id=fl.id,
                    text=f"[AICTE Query Response] {clean_resp}",
                    document_ref=final_doc_ref,
                    by_user=user.id,
                    at=now,
                )
                db.add(clarification_just)

    # Return submission to under_review (SPEC Section 10)
    sub.status = SubmissionState.UNDER_REVIEW.value

    # Notify AICTE officer
    if query.created_by:
        notif = Notification(
            user_id=query.created_by,
            type="QUERY_ANSWERED",
            payload_json={
                "query_id": query.id,
                "review_item_id": query.review_item_id,
                "submission_id": sub.id,
                "institution_name": sub.institution.name,
                "receipt_no": sub.receipt_no,
                "response": clean_resp,
            },
        )
        db.add(notif)

    db.flush()

    # Audit log entry (Hard Rule 6)
    audit_service.record(
        db=db,
        actor_id=user.id,
        actor_role=user.role,
        action="query.respond",
        entity="query",
        entity_id=query.id,
        before_json={"state": "pending", "response": None},
        after_json={
            "state": "answered",
            "response": clean_resp,
            "document_ref": final_doc_ref,
            "responded_at": now.isoformat(),
            "responded_by": user.id,
            "submission_status": sub.status,
            "review_item_status": query.review_item.status if query.review_item else None,
        },
        ip=client_ip,
    )

    publish_sse_event(
        redis_client=redis_client,
        event_type="query_answered",
        data={
            "query_id": query.id,
            "review_item_id": query.review_item_id,
            "submission_id": sub.id,
            "institution_id": institution_id,
            "state": "answered",
        },
    )

    db.commit()
    return get_institution_query_detail(
        db=db, institution_id=institution_id, query_id=query.id
    )


def get_review_justification_document(
    db: Session,
    review_item_id: int,
    justification_id: int,
    user: User,
) -> tuple[bytes, str, str]:
    """Stream justification document attached to an item in the AICTE review queue."""
    item = db.scalar(select(ReviewItem).where(ReviewItem.id == review_item_id))
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item {review_item_id} not found.",
        )

    just = db.scalar(select(Justification).where(Justification.id == justification_id))
    if not just:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Justification {justification_id} not found.",
        )

    flag_ids = [fid for fid in item.flag_ids if isinstance(fid, int)]
    if just.flag_id not in flag_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Justification does not belong to this review item.",
        )

    if not just.document_ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document attached to this justification.",
        )

    storage = get_storage()
    try:
        content = storage.get(just.document_ref)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document file {just.document_ref} not found in storage.",
        ) from None

    filename = Path(just.document_ref).name
    media_type, _ = mimetypes.guess_type(filename)
    if not media_type:
        media_type = "application/octet-stream"

    return content, filename, media_type
