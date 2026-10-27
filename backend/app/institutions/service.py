"""Business logic for institutions, courses, intake, and corrections."""

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.audit import service as audit_service
from app.institutions.schemas import (
    ApprovalStatusUpdateRequest,
    CorrectionRequestCreate,
    CorrectionRequestResolve,
    CourseCreateRequest,
    CourseIntakeUpdateRequest,
    CourseUpdateRequest,
    InstitutionUpdateRequest,
    MasterSyncResponse,
    UploadCreateRequest,
)
from app.integrations.factory import get_aicte_master_client
from app.models import (
    CorrectionRequest,
    Course,
    CourseIntake,
    CourseIntakeHistory,
    Institution,
    Notification,
    Upload,
    User,
)


def get_institution(db: Session, institution_id: int) -> Institution:
    """Fetch an institution by ID or raise HTTP 404."""
    inst = db.get(Institution, institution_id)
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution with ID {institution_id} not found",
        )
    return inst


def get_institution_by_aicte_id(db: Session, aicte_id: str) -> Institution | None:
    """Fetch an institution by its AICTE ID."""
    return db.scalar(select(Institution).where(Institution.aicte_id == aicte_id))


def list_institutions(
    db: Session,
    state: str | None = None,
    approval_status: str | None = None,
    account_status: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[Institution]]:
    """List institutions with optional filters and pagination."""
    query = select(Institution)

    if state:
        query = query.where(Institution.state == state)
    if approval_status:
        query = query.where(Institution.approval_status == approval_status)
    if account_status:
        query = query.where(Institution.account_status == account_status)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(
            Institution.name.ilike(search_term)
            | Institution.aicte_id.ilike(search_term)
            | Institution.district.ilike(search_term)
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    institutions = list(
        db.scalars(
            query.order_by(Institution.name.asc()).limit(limit).offset(offset)
        ).all()
    )
    return total, institutions


def list_courses(db: Session, institution_id: int) -> list[Course]:
    """List all approved courses for an institution."""
    get_institution(db, institution_id)
    return list(
        db.scalars(
            select(Course)
            .where(Course.institution_id == institution_id)
            .options(selectinload(Course.intakes))
            .order_by(Course.level.asc(), Course.name.asc())
        ).all()
    )


def get_course(db: Session, course_id: int, institution_id: int | None = None) -> Course:
    """Fetch an approved course or raise HTTP 404."""
    query = select(Course).where(Course.id == course_id).options(selectinload(Course.intakes))
    if institution_id is not None:
        query = query.where(Course.institution_id == institution_id)
    course = db.scalar(query)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} not found",
        )
    return course


def get_course_intakes(
    db: Session, course_id: int, academic_year: str | None = None
) -> list[CourseIntake]:
    """Retrieve approved intake records for a course."""
    query = select(CourseIntake).where(CourseIntake.course_id == course_id)
    if academic_year:
        query = query.where(CourseIntake.academic_year == academic_year)
    return list(db.scalars(query.order_by(CourseIntake.academic_year.desc())).all())


def get_course_intake(
    db: Session, course_id: int, academic_year: str
) -> CourseIntake | None:
    """Retrieve approved intake record for a course in a specific academic year."""
    return db.scalar(
        select(CourseIntake).where(
            CourseIntake.course_id == course_id,
            CourseIntake.academic_year == academic_year,
        )
    )


def get_intake_history(
    db: Session, course_id: int, academic_year: str | None = None
) -> list[CourseIntakeHistory]:
    """Retrieve intake change history for a course."""
    query = select(CourseIntakeHistory).where(CourseIntakeHistory.course_id == course_id)
    if academic_year:
        query = query.where(CourseIntakeHistory.academic_year == academic_year)
    return list(
        db.scalars(
            query.order_by(
                CourseIntakeHistory.created_at.desc(), CourseIntakeHistory.id.desc()
            )
        ).all()
    )


# =========================================================================
# AICTE-Owned Mutations (AICTE Officers Only)
# =========================================================================


def create_course(
    db: Session,
    institution_id: int,
    payload: CourseCreateRequest,
    officer: User,
    ip: str | None = None,
) -> Course:
    """Create a new approved course and optional initial intake (AICTE Officer only)."""
    get_institution(db, institution_id)

    # Check for existing course with duplicate (institution_id, name, branch, level)
    existing = db.scalar(
        select(Course).where(
            Course.institution_id == institution_id,
            Course.name == payload.name,
            Course.branch == payload.branch,
            Course.level == payload.level,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Course '{payload.name}' ({payload.branch}, {payload.level}) "
                "already exists for this institution"
            ),
        )

    course = Course(
        institution_id=institution_id,
        name=payload.name,
        level=payload.level,
        branch=payload.branch,
        duration_years=payload.duration_years,
        supernumerary_allowed=payload.supernumerary_allowed,
    )
    db.add(course)
    db.flush()

    # Initial intake
    intake = CourseIntake(
        course_id=course.id,
        academic_year=payload.academic_year,
        approved_intake=payload.approved_intake,
        supernumerary_seats_allowed=payload.supernumerary_seats_allowed,
        source="aicte_officer",
        set_by=officer.email,
    )
    db.add(intake)

    history = CourseIntakeHistory(
        course_id=course.id,
        academic_year=payload.academic_year,
        approved_intake=payload.approved_intake,
        supernumerary_seats_allowed=payload.supernumerary_seats_allowed,
        source="aicte_officer",
        set_by=officer.email,
        change_reason="Initial course approval",
    )
    db.add(history)
    db.commit()
    db.refresh(course)

    audit_service.record(
        db=db,
        action="course.create",
        actor_id=officer.id,
        actor_role=officer.role,
        entity="courses",
        entity_id=course.id,
        before_json=None,
        after_json={
            "institution_id": institution_id,
            "name": course.name,
            "level": course.level,
            "branch": course.branch,
            "duration_years": course.duration_years,
            "supernumerary_allowed": course.supernumerary_allowed,
            "academic_year": payload.academic_year,
            "approved_intake": payload.approved_intake,
            "supernumerary_seats_allowed": payload.supernumerary_seats_allowed,
        },
        ip=ip,
    )

    return course


def update_course(
    db: Session,
    course_id: int,
    payload: CourseUpdateRequest,
    officer: User,
    ip: str | None = None,
) -> Course:
    """Update course attributes (AICTE Officer only)."""
    course = get_course(db, course_id)

    before_state = {
        "name": course.name,
        "level": course.level,
        "branch": course.branch,
        "duration_years": course.duration_years,
        "supernumerary_allowed": course.supernumerary_allowed,
    }

    if payload.name is not None:
        course.name = payload.name
    if payload.level is not None:
        course.level = payload.level
    if payload.branch is not None:
        course.branch = payload.branch
    if payload.duration_years is not None:
        course.duration_years = payload.duration_years
    if payload.supernumerary_allowed is not None:
        course.supernumerary_allowed = payload.supernumerary_allowed

    db.commit()
    db.refresh(course)

    after_state = {
        "name": course.name,
        "level": course.level,
        "branch": course.branch,
        "duration_years": course.duration_years,
        "supernumerary_allowed": course.supernumerary_allowed,
    }

    audit_service.record(
        db=db,
        action="course.update",
        actor_id=officer.id,
        actor_role=officer.role,
        entity="courses",
        entity_id=course.id,
        before_json=before_state,
        after_json=after_state,
        ip=ip,
    )

    return course


def update_course_intake(
    db: Session,
    course_id: int,
    payload: CourseIntakeUpdateRequest,
    officer: User,
    ip: str | None = None,
) -> CourseIntake:
    """Update approved intake quota and log full history and audit (AICTE Officer only)."""
    course = get_course(db, course_id)

    existing_intake = db.scalar(
        select(CourseIntake).where(
            CourseIntake.course_id == course_id,
            CourseIntake.academic_year == payload.academic_year,
        )
    )

    before_state: dict[str, Any] | None = None
    if existing_intake:
        before_state = {
            "approved_intake": existing_intake.approved_intake,
            "supernumerary_seats_allowed": existing_intake.supernumerary_seats_allowed,
            "source": existing_intake.source,
            "set_by": existing_intake.set_by,
        }
        existing_intake.approved_intake = payload.approved_intake
        existing_intake.supernumerary_seats_allowed = payload.supernumerary_seats_allowed
        existing_intake.source = "aicte_officer"
        existing_intake.set_by = officer.email
        intake_record = existing_intake
    else:
        intake_record = CourseIntake(
            course_id=course_id,
            academic_year=payload.academic_year,
            approved_intake=payload.approved_intake,
            supernumerary_seats_allowed=payload.supernumerary_seats_allowed,
            source="aicte_officer",
            set_by=officer.email,
        )
        db.add(intake_record)

    # Full history record: intake is never overwritten without historical record
    history = CourseIntakeHistory(
        course_id=course_id,
        academic_year=payload.academic_year,
        approved_intake=payload.approved_intake,
        supernumerary_seats_allowed=payload.supernumerary_seats_allowed,
        source="aicte_officer",
        set_by=officer.email,
        change_reason=payload.change_reason or "Intake revised by AICTE officer",
    )
    db.add(history)

    # Notify institution of intake change
    notification = Notification(
        institution_id=course.institution_id,
        type="intake_change",
        payload_json={
            "course_id": course.id,
            "course_name": course.name,
            "academic_year": payload.academic_year,
            "new_approved_intake": payload.approved_intake,
            "new_supernumerary": payload.supernumerary_seats_allowed,
            "reason": payload.change_reason,
            "officer": officer.email,
        },
    )
    db.add(notification)

    db.commit()
    db.refresh(intake_record)

    after_state = {
        "approved_intake": intake_record.approved_intake,
        "supernumerary_seats_allowed": intake_record.supernumerary_seats_allowed,
        "source": intake_record.source,
        "set_by": intake_record.set_by,
        "academic_year": intake_record.academic_year,
        "change_reason": payload.change_reason,
    }

    audit_service.record(
        db=db,
        action="intake.update",
        actor_id=officer.id,
        actor_role=officer.role,
        entity="course_intake",
        entity_id=intake_record.id,
        before_json=before_state,
        after_json=after_state,
        ip=ip,
    )

    return intake_record


def update_approval_status(
    db: Session,
    institution_id: int,
    payload: ApprovalStatusUpdateRequest,
    officer: User,
    ip: str | None = None,
) -> Institution:
    """Adjust institution approval status (active, suspended, withdrawn, expired)."""
    institution = get_institution(db, institution_id)

    before_state = {
        "approval_status": institution.approval_status,
        "approval_valid_to": institution.approval_valid_to.isoformat()
        if institution.approval_valid_to
        else None,
    }

    institution.approval_status = payload.approval_status
    if payload.approval_valid_to is not None:
        institution.approval_valid_to = payload.approval_valid_to

    # Alert notification for non-active approval states
    if payload.approval_status in {"suspended", "withdrawn", "expired"}:
        alert_notif = Notification(
            institution_id=institution.id,
            type="approval_status_alert",
            payload_json={
                "previous_status": before_state["approval_status"],
                "new_status": payload.approval_status,
                "reason": payload.reason,
                "message": (
                    f"Approval status changed to {payload.approval_status}. "
                    "New uploads and data modifications are now blocked."
                ),
            },
        )
        db.add(alert_notif)

    db.commit()
    db.refresh(institution)

    after_state = {
        "approval_status": institution.approval_status,
        "approval_valid_to": institution.approval_valid_to.isoformat()
        if institution.approval_valid_to
        else None,
        "reason": payload.reason,
    }

    audit_service.record(
        db=db,
        action="institution.approval_status_update",
        actor_id=officer.id,
        actor_role=officer.role,
        entity="institutions",
        entity_id=institution.id,
        before_json=before_state,
        after_json=after_state,
        ip=ip,
    )

    return institution


def update_institution_info(
    db: Session,
    institution_id: int,
    payload: InstitutionUpdateRequest,
    officer: User,
    ip: str | None = None,
) -> Institution:
    """Update AICTE-owned official institution details (AICTE Officer only)."""
    inst = get_institution(db, institution_id)

    before_state = {
        "official_email": inst.official_email,
        "official_phone": inst.official_phone,
        "head_name": inst.head_name,
        "address": inst.address,
        "affiliating_university": inst.affiliating_university,
        "approval_status": inst.approval_status,
        "approval_valid_to": inst.approval_valid_to.isoformat()
        if inst.approval_valid_to
        else None,
    }

    if payload.official_email is not None:
        inst.official_email = payload.official_email
    if payload.official_phone is not None:
        inst.official_phone = payload.official_phone
    if payload.head_name is not None:
        inst.head_name = payload.head_name
    if payload.address is not None:
        inst.address = payload.address
    if payload.affiliating_university is not None:
        inst.affiliating_university = payload.affiliating_university
    if payload.approval_status is not None:
        inst.approval_status = payload.approval_status
    if payload.approval_valid_to is not None:
        inst.approval_valid_to = payload.approval_valid_to

    db.commit()
    db.refresh(inst)

    after_state = {
        "official_email": inst.official_email,
        "official_phone": inst.official_phone,
        "head_name": inst.head_name,
        "address": inst.address,
        "affiliating_university": inst.affiliating_university,
        "approval_status": inst.approval_status,
        "approval_valid_to": inst.approval_valid_to.isoformat()
        if inst.approval_valid_to
        else None,
    }

    audit_service.record(
        db=db,
        action="institution.update",
        actor_id=officer.id,
        actor_role=officer.role,
        entity="institutions",
        entity_id=inst.id,
        before_json=before_state,
        after_json=after_state,
        ip=ip,
    )

    return inst


# =========================================================================
# Mock AICTE Master Sync
# =========================================================================


def sync_master_data(
    db: Session,
    aicte_id: str | None,
    academic_year: str,
    officer: User,
    ip: str | None = None,
) -> MasterSyncResponse:
    """Sync institution and course intake records from external AICTE Master Registry."""
    master_client = get_aicte_master_client()

    if aicte_id:
        record = master_client.get_institution(aicte_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Institution '{aicte_id}' not found in external AICTE Master registry",
            )
        master_institutions = [record]
    else:
        master_institutions = master_client.list_institutions()

    synced_institutions = 0
    synced_courses = 0
    synced_intakes = 0
    details: list[str] = []

    for master_inst in master_institutions:
        inst = db.scalar(select(Institution).where(Institution.aicte_id == master_inst.aicte_id))
        if inst is None:
            inst = Institution(
                aicte_id=master_inst.aicte_id,
                name=master_inst.name,
                state=master_inst.state,
                district=master_inst.district,
                address=master_inst.address,
                official_email=master_inst.official_email,
                official_phone=master_inst.official_phone,
                head_name=master_inst.head_name,
                affiliating_university=master_inst.affiliating_university,
                approval_status=master_inst.approval_status,
                approval_valid_to=master_inst.approval_valid_to,
                account_status="not_activated",
            )
            db.add(inst)
            db.flush()
            details.append(f"Created institution {inst.aicte_id} ({inst.name})")
        else:
            inst.name = master_inst.name
            inst.state = master_inst.state
            inst.district = master_inst.district
            inst.address = master_inst.address
            inst.official_email = master_inst.official_email
            inst.official_phone = master_inst.official_phone
            inst.head_name = master_inst.head_name
            inst.affiliating_university = master_inst.affiliating_university
            inst.approval_status = master_inst.approval_status
            inst.approval_valid_to = master_inst.approval_valid_to
            db.flush()
            details.append(f"Updated institution {inst.aicte_id}")

        synced_institutions += 1

        # Sync courses
        for course_info in master_inst.courses:
            course = db.scalar(
                select(Course).where(
                    Course.institution_id == inst.id,
                    Course.name == course_info.name,
                    Course.branch == course_info.branch,
                    Course.level == course_info.level,
                )
            )
            if course is None:
                course = Course(
                    institution_id=inst.id,
                    name=course_info.name,
                    level=course_info.level,
                    branch=course_info.branch,
                    duration_years=course_info.duration_years,
                    supernumerary_allowed=course_info.supernumerary_allowed,
                )
                db.add(course)
                db.flush()
                synced_courses += 1

            # Sync intake for specified academic year
            intake = db.scalar(
                select(CourseIntake).where(
                    CourseIntake.course_id == course.id,
                    CourseIntake.academic_year == academic_year,
                )
            )
            if intake is None:
                intake = CourseIntake(
                    course_id=course.id,
                    academic_year=academic_year,
                    approved_intake=course_info.approved_intake,
                    supernumerary_seats_allowed=course_info.supernumerary_seats_allowed,
                    source="aicte_master",
                    set_by="master_sync",
                )
                db.add(intake)
                synced_intakes += 1

                # History row
                history = CourseIntakeHistory(
                    course_id=course.id,
                    academic_year=academic_year,
                    approved_intake=course_info.approved_intake,
                    supernumerary_seats_allowed=course_info.supernumerary_seats_allowed,
                    source="aicte_master",
                    set_by="master_sync",
                    change_reason="AICTE Master Registry sync",
                )
                db.add(history)
            elif (
                intake.approved_intake != course_info.approved_intake
                or intake.supernumerary_seats_allowed != course_info.supernumerary_seats_allowed
            ):
                intake.approved_intake = course_info.approved_intake
                intake.supernumerary_seats_allowed = course_info.supernumerary_seats_allowed
                intake.source = "aicte_master"
                intake.set_by = "master_sync"
                synced_intakes += 1

                history = CourseIntakeHistory(
                    course_id=course.id,
                    academic_year=academic_year,
                    approved_intake=course_info.approved_intake,
                    supernumerary_seats_allowed=course_info.supernumerary_seats_allowed,
                    source="aicte_master",
                    set_by="master_sync",
                    change_reason="AICTE Master Registry sync update",
                )
                db.add(history)

    db.commit()

    audit_service.record(
        db=db,
        action="institution.sync",
        actor_id=officer.id,
        actor_role=officer.role,
        entity="institutions",
        entity_id=aicte_id or "all",
        before_json=None,
        after_json={
            "synced_institutions": synced_institutions,
            "synced_courses": synced_courses,
            "synced_intakes": synced_intakes,
            "academic_year": academic_year,
        },
        ip=ip,
    )

    return MasterSyncResponse(
        status="success",
        synced_institutions=synced_institutions,
        synced_courses=synced_courses,
        synced_intakes=synced_intakes,
        details=details[:50],  # Return up to 50 detail lines
    )


# =========================================================================
# Correction Requests (Colleges create, AICTE resolves)
# =========================================================================


def create_correction_request(
    db: Session,
    institution_id: int,
    payload: CorrectionRequestCreate,
    user: User,
    ip: str | None = None,
) -> CorrectionRequest:
    """College files a correction request for AICTE-owned data."""
    get_institution(db, institution_id)

    req = CorrectionRequest(
        institution_id=institution_id,
        kind=payload.kind,
        payload_json=payload.payload_json,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    audit_service.record(
        db=db,
        action="correction_request.create",
        actor_id=user.id,
        actor_role=user.role,
        entity="correction_requests",
        entity_id=req.id,
        before_json=None,
        after_json={
            "institution_id": institution_id,
            "kind": req.kind,
            "payload_json": req.payload_json,
            "status": req.status,
        },
        ip=ip,
    )

    return req


def list_correction_requests(
    db: Session,
    institution_id: int | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[CorrectionRequest]]:
    """List correction requests with optional institution and status filters."""
    query = select(CorrectionRequest)
    if institution_id is not None:
        query = query.where(CorrectionRequest.institution_id == institution_id)
    if status_filter:
        query = query.where(CorrectionRequest.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    requests = list(
        db.scalars(
            query.order_by(CorrectionRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return total, requests


def get_correction_request(db: Session, request_id: int) -> CorrectionRequest:
    """Fetch a correction request by ID or raise HTTP 404."""
    req = db.get(CorrectionRequest, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Correction request with ID {request_id} not found",
        )
    return req


def resolve_correction_request(
    db: Session,
    request_id: int,
    payload: CorrectionRequestResolve,
    officer: User,
    ip: str | None = None,
) -> CorrectionRequest:
    """AICTE Officer approves or rejects a college correction request."""
    req = get_correction_request(db, request_id)
    if req.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Correction request {request_id} has already been resolved "
                f"with status '{req.status}'"
            ),
        )

    before_state = {
        "status": req.status,
        "resolved_by": req.resolved_by,
        "resolved_at": req.resolved_at.isoformat() if req.resolved_at else None,
    }

    req.status = payload.status
    req.resolved_by = officer.id
    req.resolved_at = datetime.now()

    # If approved and apply_changes is requested, apply the changes to AICTE-owned data
    applied_changes: dict[str, Any] = {}
    if payload.status == "approved" and payload.apply_changes:
        inst = db.get(Institution, req.institution_id)
        data = req.payload_json

        if inst:
            # Contact or head updates
            for field in ["official_email", "official_phone", "head_name", "address"]:
                if field in data and isinstance(data[field], str):
                    setattr(inst, field, data[field])
                    applied_changes[field] = data[field]

            # Intake correction
            if req.kind == "intake" and "course_id" in data and "approved_intake" in data:
                course_id = int(data["course_id"])
                year = str(data.get("academic_year", "2026-27"))
                intake_val = int(data["approved_intake"])
                supernum_val = int(data.get("supernumerary_seats_allowed", 0))

                course_intake = db.scalar(
                    select(CourseIntake).where(
                        CourseIntake.course_id == course_id,
                        CourseIntake.academic_year == year,
                    )
                )
                if course_intake:
                    course_intake.approved_intake = intake_val
                    course_intake.supernumerary_seats_allowed = supernum_val
                    course_intake.source = "correction_request"
                    course_intake.set_by = officer.email
                else:
                    course_intake = CourseIntake(
                        course_id=course_id,
                        academic_year=year,
                        approved_intake=intake_val,
                        supernumerary_seats_allowed=supernum_val,
                        source="correction_request",
                        set_by=officer.email,
                    )
                    db.add(course_intake)

                # History row
                change_msg = payload.decision_note or "No note"
                history = CourseIntakeHistory(
                    course_id=course_id,
                    academic_year=year,
                    approved_intake=intake_val,
                    supernumerary_seats_allowed=supernum_val,
                    source="correction_request",
                    set_by=officer.email,
                    change_reason=f"Approved correction request #{req.id}: {change_msg}",
                )
                db.add(history)
                applied_changes["intake"] = {
                    "course_id": course_id,
                    "academic_year": year,
                    "approved_intake": intake_val,
                }

    # Notify institution
    notification = Notification(
        institution_id=req.institution_id,
        type="correction_request_resolved",
        payload_json={
            "request_id": req.id,
            "kind": req.kind,
            "status": req.status,
            "decision_note": payload.decision_note,
            "applied_changes": applied_changes,
        },
    )
    db.add(notification)

    db.commit()
    db.refresh(req)

    after_state = {
        "status": req.status,
        "resolved_by": req.resolved_by,
        "resolved_at": req.resolved_at.isoformat() if req.resolved_at else None,
        "decision_note": payload.decision_note,
        "applied_changes": applied_changes,
    }

    audit_service.record(
        db=db,
        action="correction_request.resolve",
        actor_id=officer.id,
        actor_role=officer.role,
        entity="correction_requests",
        entity_id=req.id,
        before_json=before_state,
        after_json=after_state,
        ip=ip,
    )

    return req


# =========================================================================
# Upload Gate / Approval Status Enforcement
# =========================================================================


def check_institution_can_upload(institution: Institution) -> None:
    """Enforce that only institutions with 'active' approval status can upload data.

    Spec 6: If approval becomes suspended, withdrawn or expired: new uploads are blocked.
    Raises:
        HTTPException 403: If institution approval status is not 'active'.
    """
    if institution.approval_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Institution approval status is '{institution.approval_status}'. "
                "New student uploads and submissions are blocked."
            ),
        )


def create_upload_session(
    db: Session,
    institution_id: int,
    payload: UploadCreateRequest,
    user: User,
) -> Upload:
    """Create a batch upload session after checking institution approval status."""
    inst = get_institution(db, institution_id)
    check_institution_can_upload(inst)

    upload = Upload(
        institution_id=institution_id,
        filename=payload.filename,
        row_count=payload.row_count,
        status="processing",
        uploaded_by=user.id,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    audit_service.record(
        db=db,
        action="upload.create",
        actor_id=user.id,
        actor_role=user.role,
        entity="uploads",
        entity_id=upload.id,
        before_json=None,
        after_json={
            "institution_id": institution_id,
            "filename": upload.filename,
            "row_count": upload.row_count,
            "status": upload.status,
        },
    )

    return upload
