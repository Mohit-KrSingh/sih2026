"""Service logic for post-lock student change requests."""

import os
import uuid
from datetime import UTC, date, datetime

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.audit import record as record_audit
from app.auth.schemas import Role, UserResponse
from app.auth.security import decrypt_dob, encrypt_dob
from app.integrations.factory import get_storage
from app.models import ChangeRequest, Course, Institution, Notification, Student
from app.students.change_request_schemas import (
    ChangeRequestInstitutionInfo,
    ChangeRequestListResponse,
    ChangeRequestResponse,
    ChangeRequestStudentInfo,
)
from app.students.duplicate_service import resolve_duplicate_flags_on_status_change

ALLOWED_FIELDS = {
    "status",
    "name",
    "dob",
    "gender",
    "enrolment_no",
    "admission_date",
    "admission_mode",
    "seat_type",
    "reservation_category",
    "nri",
    "oci",
    "foreign_national",
    "fn_country",
    "course_id",
}

VALID_STATUSES = {
    "withdrawn",
    "transferred",
    "graduated",
    "submitted",
    "verified",
    "verified_with_exception",
}


def _map_change_request_to_response(cr: ChangeRequest) -> ChangeRequestResponse:
    """Map SQLAlchemy ChangeRequest model to Pydantic response."""
    student_info = None
    inst_info = None

    if cr.student:
        s = cr.student
        c_name = s.course.name if s.course else None
        student_info = ChangeRequestStudentInfo(
            id=s.id,
            apaar_id=s.apaar_id,
            name=s.name,
            course_id=s.course_id,
            course_name=c_name,
            academic_year=s.academic_year,
            status=s.status,
            is_locked=s.is_locked,
        )
        if s.institution:
            inst_info = ChangeRequestInstitutionInfo(
                id=s.institution.id,
                aicte_id=s.institution.aicte_id,
                name=s.institution.name,
                state=s.institution.state,
            )

    decided_by_email = cr.decider.email if cr.decider else None

    return ChangeRequestResponse(
        id=cr.id,
        student_id=cr.student_id,
        student=student_info,
        institution_id=cr.student.institution_id if cr.student else 0,
        institution=inst_info,
        field=cr.field,
        old_value=cr.old_value,
        new_value=cr.new_value,
        reason=cr.reason,
        status=cr.status,
        decided_by=cr.decided_by,
        decided_by_email=decided_by_email,
        decided_at=cr.decided_at,
        document_ref=cr.document_ref,
        decision_note=cr.decision_note,
        created_at=cr.created_at,
        updated_at=cr.updated_at,
    )


async def create_change_request(
    db: Session,
    institution_id: int,
    student_id: int,
    field: str,
    new_value: str,
    reason: str,
    user: UserResponse,
    document_file: UploadFile | None = None,
    document_ref: str | None = None,
) -> ChangeRequestResponse:
    """Create a post-lock change request for a student.

    - Validates institution account status is active.
    - Ensures student exists and belongs to this institution.
    - Ensures student is locked (SPEC.md Section 10). Unlocked records must be edited directly.
    - Validates target field and value syntax.
    - Uploads evidence document behind Storage interface if provided.
    - Persists pending change request and records hash-chained audit log.
    """
    inst = db.get(Institution, institution_id)
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution with ID {institution_id} not found",
        )
    if inst.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Institution account is not active",
        )

    student = db.get(Student, student_id)
    if not student or student.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {student_id} not found in this institution",
        )

    # Only locked / submitted students require a formal change request
    valid_sub_statuses = {
        "submitted",
        "submitted_with_exceptions",
        "under_review",
        "accepted",
        "escalated",
    }
    if not student.is_locked and (
        student.submission is None or student.submission.status not in valid_sub_statuses
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Student record is not locked. Unlocked draft records can be modified directly "
                "without a change request."
            ),
        )

    # Validate field
    clean_field = field.strip()
    if clean_field not in ALLOWED_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Field '{clean_field}' cannot be modified via change request. "
                f"Allowed fields: {sorted(ALLOWED_FIELDS)}"
            ),
        )

    clean_new_val = new_value.strip()
    if not clean_new_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New value cannot be empty",
        )

    # Check for existing pending request for this student & field
    pending_existing = db.scalars(
        select(ChangeRequest).where(
            ChangeRequest.student_id == student.id,
            ChangeRequest.field == clean_field,
            ChangeRequest.status == "pending",
        )
    ).first()
    if pending_existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A pending change request (#{pending_existing.id}) already exists "
                f"for this student's '{clean_field}'."
            ),
        )

    # Determine old_value and validate new_value
    old_val: str | None = None
    if clean_field == "dob":
        if student.dob_encrypted:
            try:
                old_val = str(decrypt_dob(student.dob_encrypted))
            except Exception:
                old_val = None
        try:
            parsed_dob = date.fromisoformat(clean_new_val)
            if parsed_dob > date.today():
                raise ValueError("Date of birth cannot be in the future")
            clean_new_val = parsed_dob.isoformat()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date of birth format: {e}",
            ) from None

    elif clean_field == "status":
        old_val = student.status
        status_candidate = clean_new_val.lower()
        if status_candidate not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid student status '{clean_new_val}'. "
                    f"Allowed: {sorted(VALID_STATUSES)}"
                ),
            )
        clean_new_val = status_candidate

    elif clean_field == "gender":
        old_val = student.gender
        if clean_new_val not in {"Male", "Female", "Other"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gender must be 'Male', 'Female', or 'Other'",
            )

    elif clean_field == "seat_type":
        old_val = student.seat_type
        if clean_new_val not in {"Regular", "Supernumerary"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seat type must be 'Regular' or 'Supernumerary'",
            )

    elif clean_field == "reservation_category":
        old_val = student.reservation_category
        if clean_new_val not in {"General", "OBC", "SC", "ST", "EWS"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category must be 'General', 'OBC', 'SC', 'ST', or 'EWS'",
            )

    elif clean_field in {"nri", "oci", "foreign_national"}:
        old_val = getattr(student, clean_field, None)
        if clean_new_val not in {"Yes", "No"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{clean_field} must be 'Yes' or 'No'",
            )

    elif clean_field == "course_id":
        old_val = str(student.course_id) if student.course_id else None
        try:
            target_cid = int(clean_new_val)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="course_id must be an integer",
            ) from None
        target_course = db.get(Course, target_cid)
        if not target_course or target_course.institution_id != institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target course not found or does not belong to this institution",
            )

    else:
        raw_old = getattr(student, clean_field, None)
        old_val = str(raw_old) if raw_old is not None else None

    # Handle document upload via Storage interface
    final_doc_ref = document_ref
    if document_file is not None:
        storage = get_storage()
        file_bytes = await document_file.read()
        if len(file_bytes) > 10 * 1024 * 1024:  # 10 MB limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Evidence document exceeds maximum permitted size of 10 MB",
            )
        _, ext = os.path.splitext(document_file.filename or "")
        ext = ext if ext else ".pdf"
        storage_path = (
            f"change_requests/inst_{institution_id}/{uuid.uuid4().hex[:12]}_{document_file.filename}"
        )
        final_doc_ref = storage.save(
            path=storage_path,
            content=file_bytes,
            content_type=document_file.content_type or "application/octet-stream",
        )

    # Persist change request
    cr = ChangeRequest(
        student_id=student.id,
        field=clean_field,
        old_value=old_val,
        new_value=clean_new_val,
        reason=reason.strip(),
        status="pending",
        document_ref=final_doc_ref,
    )
    db.add(cr)
    db.flush()

    # Record hash-chained audit log
    record_audit(
        db=db,
        action="change_request.created",
        actor_id=user.id,
        actor_role=user.role,
        entity="ChangeRequest",
        entity_id=cr.id,
        after_json={
            "student_id": student.id,
            "apaar_id": student.apaar_id,
            "field": clean_field,
            "old_value": old_val,
            "new_value": clean_new_val,
            "reason": reason.strip(),
            "document_ref": final_doc_ref,
        },
    )

    # Send notification to college confirming receipt
    notif = Notification(
        institution_id=institution_id,
        type="CHANGE_REQUEST_SUBMITTED",
        payload_json={
            "change_request_id": cr.id,
            "student_id": student.id,
            "student_name": student.name,
            "apaar_id": student.apaar_id,
            "field": clean_field,
            "new_value": clean_new_val,
            "message": (
                f"Change request #{cr.id} submitted for student {student.name} ({clean_field})."
            ),
        },
    )
    db.add(notif)
    db.commit()

    # Eager reload for response mapping
    reloaded_cr = db.scalars(
        select(ChangeRequest)
        .options(
            joinedload(ChangeRequest.student).joinedload(Student.course),
            joinedload(ChangeRequest.student).joinedload(Student.institution),
            joinedload(ChangeRequest.decider),
        )
        .where(ChangeRequest.id == cr.id)
    ).first()

    return _map_change_request_to_response(reloaded_cr or cr)


def list_change_requests(
    db: Session,
    institution_id: int | None = None,
    status_filter: str | None = None,
    academic_year: str | None = None,
    student_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ChangeRequestListResponse:
    """List change requests with optional filtering and pagination."""
    query = (
        select(ChangeRequest)
        .join(ChangeRequest.student)
        .options(
            joinedload(ChangeRequest.student).joinedload(Student.course),
            joinedload(ChangeRequest.student).joinedload(Student.institution),
            joinedload(ChangeRequest.decider),
        )
    )

    count_query = select(func.count(ChangeRequest.id)).join(ChangeRequest.student)

    if institution_id is not None:
        query = query.where(Student.institution_id == institution_id)
        count_query = count_query.where(Student.institution_id == institution_id)

    if status_filter:
        query = query.where(ChangeRequest.status == status_filter.strip())
        count_query = count_query.where(ChangeRequest.status == status_filter.strip())

    if academic_year:
        query = query.where(Student.academic_year == academic_year.strip())
        count_query = count_query.where(Student.academic_year == academic_year.strip())

    if student_id is not None:
        query = query.where(ChangeRequest.student_id == student_id)
        count_query = count_query.where(ChangeRequest.student_id == student_id)

    total = db.scalar(count_query) or 0
    items = (
        db.scalars(
            query.order_by(ChangeRequest.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )

    return ChangeRequestListResponse(
        items=[_map_change_request_to_response(cr) for cr in items],
        total=total,
        limit=limit,
        offset=offset,
    )


def get_change_request_detail(
    db: Session,
    request_id: int,
    institution_id: int | None = None,
) -> ChangeRequestResponse:
    """Fetch detail for a single change request with IDOR access checks."""
    cr = db.scalars(
        select(ChangeRequest)
        .options(
            joinedload(ChangeRequest.student).joinedload(Student.course),
            joinedload(ChangeRequest.student).joinedload(Student.institution),
            joinedload(ChangeRequest.decider),
        )
        .where(ChangeRequest.id == request_id)
    ).first()

    if not cr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request with ID {request_id} not found",
        )

    if institution_id is not None and cr.student.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: this change request belongs to another institution",
        )

    return _map_change_request_to_response(cr)


def decide_change_request(
    db: Session,
    request_id: int,
    decision: str,
    decision_note: str | None,
    officer: UserResponse,
) -> ChangeRequestResponse:
    """Approve or reject a student change request.

    - Only accessible by AICTE officers and admins.
    - If approved:
      * Changes are applied to the student record.
      * If field is status and status in (withdrawn, transferred):
        Duplicate enrolment flags are resolved across institutions.
      * If field is dob: Fernet encryption is updated.
      * Historical before and after state recorded in audit log.
      * ChangeRequest table preserves the permanent historical record.
    - If rejected:
      * ChangeRequest status becomes 'rejected'.
      * Officer note recorded and college notified.
    """
    if officer.role not in [Role.AICTE_ADMIN, Role.AICTE_OFFICER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only AICTE officers can review change requests",
        )

    cr = db.scalars(
        select(ChangeRequest)
        .options(
            joinedload(ChangeRequest.student).joinedload(Student.course),
            joinedload(ChangeRequest.student).joinedload(Student.institution),
            joinedload(ChangeRequest.decider),
        )
        .where(ChangeRequest.id == request_id)
    ).first()

    if not cr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request with ID {request_id} not found",
        )

    if cr.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Change request #{request_id} has already been decided ({cr.status})",
        )

    now = datetime.now(UTC)
    student = cr.student
    inst_id = student.institution_id

    if decision == "approve":
        cr.status = "approved"
        cr.decided_by = officer.id
        cr.decided_at = now
        cr.decision_note = decision_note.strip() if decision_note else None

        # Apply change to student record
        if cr.field == "dob":
            student.dob_encrypted = encrypt_dob(cr.new_value)
        elif cr.field == "status":
            new_st = cr.new_value.lower()
            student.status = new_st
            # If student is withdrawn or transferred, resolve duplicate flags per SPEC 9.3 & T16
            if new_st in ("withdrawn", "transferred"):
                resolve_duplicate_flags_on_status_change(db, student, new_st)
        elif cr.field == "course_id":
            student.course_id = int(cr.new_value)
        else:
            setattr(student, cr.field, cr.new_value)

        # Audit log recording before and after values (history preservation)
        record_audit(
            db=db,
            action="change_request.approved",
            actor_id=officer.id,
            actor_role=officer.role,
            entity="ChangeRequest",
            entity_id=cr.id,
            before_json={
                "student_id": student.id,
                "apaar_id": student.apaar_id,
                "field": cr.field,
                "value": cr.old_value,
            },
            after_json={
                "student_id": student.id,
                "apaar_id": student.apaar_id,
                "field": cr.field,
                "value": cr.new_value,
                "decision_note": cr.decision_note,
            },
        )

        # College notification
        notif = Notification(
            institution_id=inst_id,
            type="CHANGE_REQUEST_APPROVED",
            payload_json={
                "change_request_id": cr.id,
                "student_id": student.id,
                "student_name": student.name,
                "apaar_id": student.apaar_id,
                "field": cr.field,
                "new_value": cr.new_value,
                "message": (
                    f"Change request #{cr.id} for {student.name} ({cr.field}) "
                    f"was approved by AICTE."
                ),
            },
        )
        db.add(notif)

    elif decision == "reject":
        cr.status = "rejected"
        cr.decided_by = officer.id
        cr.decided_at = now
        cr.decision_note = decision_note.strip() if decision_note else "Request rejected by AICTE."

        record_audit(
            db=db,
            action="change_request.rejected",
            actor_id=officer.id,
            actor_role=officer.role,
            entity="ChangeRequest",
            entity_id=cr.id,
            before_json={"status": "pending"},
            after_json={
                "status": "rejected",
                "decision_note": cr.decision_note,
            },
        )

        notif = Notification(
            institution_id=inst_id,
            type="CHANGE_REQUEST_REJECTED",
            payload_json={
                "change_request_id": cr.id,
                "student_id": student.id,
                "student_name": student.name,
                "apaar_id": student.apaar_id,
                "field": cr.field,
                "reason": cr.decision_note,
                "message": (
                    f"Change request #{cr.id} for {student.name} ({cr.field}) "
                    f"was rejected: {cr.decision_note}"
                ),
            },
        )
        db.add(notif)

    db.commit()
    db.refresh(cr)

    return _map_change_request_to_response(cr)
