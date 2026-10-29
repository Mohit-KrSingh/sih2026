"""Business logic for institutions, courses, intake, corrections, and activation."""

import base64
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import redis
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.audit import service as audit_service
from app.auth.otp import store_and_send_otp, verify_otp
from app.auth.schemas import Role
from app.auth.security import hash_password
from app.auth.totp import generate_totp_secret, get_totp_uri
from app.config import get_settings
from app.institutions.schemas import (
    ActivationDecisionResponse,
    ActivationInitiateResponse,
    ActivationOtpVerifyResponse,
    ActivationStatusResponse,
    ActivationSubmitRequest,
    ApprovalStatusUpdateRequest,
    ContactChangeRequestCreate,
    CorrectionRequestCreate,
    CorrectionRequestResolve,
    CourseCreateRequest,
    CourseIntakeUpdateRequest,
    CourseUpdateRequest,
    InstitutionUpdateRequest,
    MasterSyncResponse,
    StaffCreateRequest,
    StaffUpdateRequest,
    UploadCreateRequest,
)
from app.integrations.factory import (
    get_aicte_master_client,
    get_identity_verifier,
    get_otp_sender,
    get_storage,
)
from app.models import (
    ActivationRequest,
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
        db.scalars(query.order_by(Institution.name.asc()).limit(limit).offset(offset)).all()
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


def get_course_intake(db: Session, course_id: int, academic_year: str) -> CourseIntake | None:
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
            query.order_by(CourseIntakeHistory.created_at.desc(), CourseIntakeHistory.id.desc())
        ).all()
    )


# AICTE-Owned Mutations (AICTE Officers Only)


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
        "approval_valid_to": inst.approval_valid_to.isoformat() if inst.approval_valid_to else None,
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
        "approval_valid_to": inst.approval_valid_to.isoformat() if inst.approval_valid_to else None,
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


# Mock AICTE Master Sync


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


# Correction Requests (Colleges create, AICTE resolves)


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
            query.order_by(CorrectionRequest.created_at.desc()).limit(limit).offset(offset)
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


# Upload Gate / Approval Status Enforcement


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


# Activation Management (Spec 11, TASKS.md T08)

ACTIVATION_TOKEN_EXPIRE_MINUTES = 30


def mask_email(email: str) -> str:
    """Mask email address for privacy display (e.g. o***@example.edu)."""
    if not email or "@" not in email:
        return "***"
    username, domain = email.strip().split("@", 1)
    if len(username) <= 2:
        masked_user = username[0] + "***"
    else:
        masked_user = username[0] + "***" + username[-1]
    return f"{masked_user}@{domain}"


def mask_phone(phone: str) -> str:
    """Mask phone number for privacy display (e.g. ******3210)."""
    if not phone:
        return "****"
    clean = phone.strip()
    if len(clean) <= 4:
        return "****"
    return "*" * (len(clean) - 4) + clean[-4:]


def create_activation_token(institution_id: int, aicte_id: str) -> str:
    """Create a tamper-proof signed activation session token."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": f"activation:{aicte_id}",
        "institution_id": institution_id,
        "aicte_id": aicte_id,
        "purpose": "college_activation",
        "type": "activation_session",
        "exp": now + timedelta(minutes=ACTIVATION_TOKEN_EXPIRE_MINUTES),
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_activation_token(token: str) -> dict[str, Any]:
    """Decode and validate an activation session token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except (jwt.PyJWTError, Exception) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired activation session token. Please verify OTP again.",
        ) from exc

    if (
        payload.get("type") != "activation_session"
        or payload.get("purpose") != "college_activation"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid activation token type",
        )
    return payload


def initiate_activation(
    db: Session,
    redis_client: redis.Redis,
    aicte_id: str,
) -> ActivationInitiateResponse:
    """Initiate college activation claim by AICTE ID.

    Spec 11:
    1. Enter AICTE institution ID. Unknown ID: rejected immediately.
    2. OTP goes ONLY to official email and phone already on file with AICTE,
       never to a typed-in address.
    3. Rules: approval must be active for the year.
    """
    cleaned_id = aicte_id.strip()

    # 1. Look up institution in DB or sync from external AICTE Master Registry
    inst = db.scalar(select(Institution).where(Institution.aicte_id == cleaned_id))
    if inst is None:
        master_client = get_aicte_master_client()
        master_record = master_client.get_institution(cleaned_id)
        if not master_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Institution ID '{cleaned_id}' not found in official AICTE registry",
            )
        # Create not_activated institution record from master registry
        inst = Institution(
            aicte_id=master_record.aicte_id,
            name=master_record.name,
            state=master_record.state,
            district=master_record.district,
            address=master_record.address,
            official_email=master_record.official_email,
            official_phone=master_record.official_phone,
            head_name=master_record.head_name,
            affiliating_university=master_record.affiliating_university,
            approval_status=master_record.approval_status,
            approval_valid_to=master_record.approval_valid_to,
            account_status="not_activated",
        )
        db.add(inst)
        db.flush()

    # 2. Check if already activated
    if inst.account_status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Institution '{inst.name}' is already activated. Please log in.",
        )

    # 3. Check approval status (SPEC 11: approval must be active for the year)
    if inst.approval_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Institution approval status is '{inst.approval_status}'. "
                "Only institutions with active AICTE approval can activate an account."
            ),
        )

    # 4. Check if pending activation request exists
    pending_request = db.scalar(
        select(ActivationRequest).where(
            ActivationRequest.institution_id == inst.id,
            ActivationRequest.status == "pending",
        )
    )
    if pending_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"An activation request for '{inst.name}' is already pending review "
                "by AICTE officers. Please wait for official approval."
            ),
        )

    # 5. OTP goes ONLY to official email and phone already on file with AICTE
    # Caller CANNOT specify recipient address.
    official_email = inst.official_email
    official_phone = inst.official_phone

    if not official_email:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No official email on file for institution",
        )

    # Dispatch to on-file email
    store_and_send_otp(
        db=db,
        redis_client=redis_client,
        recipient=official_email,
        channel="email",
        purpose="activation",
        context=f"College account activation claim for AICTE ID {inst.aicte_id}",
    )

    # Also dispatch to on-file phone if available
    if official_phone:
        store_and_send_otp(
            db=db,
            redis_client=redis_client,
            recipient=official_phone,
            channel="sms",
            purpose="activation",
            context=f"College activation OTP for {inst.aicte_id}",
        )

    return ActivationInitiateResponse(
        aicte_id=inst.aicte_id,
        institution_name=inst.name,
        masked_email=mask_email(official_email),
        masked_phone=mask_phone(official_phone),
        status="otp_dispatched",
        message="One-time verification code sent to official contacts on file with AICTE.",
    )


def verify_activation_otp(
    db: Session,
    redis_client: redis.Redis,
    aicte_id: str,
    otp_code: str,
) -> ActivationOtpVerifyResponse:
    """Verify OTP code sent to official on-file contact and issue activation session token."""
    cleaned_id = aicte_id.strip()
    inst = db.scalar(select(Institution).where(Institution.aicte_id == cleaned_id))
    if inst is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution ID '{cleaned_id}' not found",
        )

    is_valid, msg, remaining = verify_otp(
        redis_client=redis_client,
        recipient=inst.official_email,
        purpose="activation",
        code=otp_code.strip(),
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OTP verification failed: {msg}",
        )

    activation_token = create_activation_token(inst.id, inst.aicte_id)

    return ActivationOtpVerifyResponse(
        verified=True,
        activation_token=activation_token,
        aicte_id=inst.aicte_id,
        institution_name=inst.name,
        head_name=inst.head_name,
        message="OTP verified successfully. Proceed with signatory check and letter upload.",
    )


def submit_activation_claim(
    db: Session,
    payload: ActivationSubmitRequest,
    file_bytes: bytes | None = None,
    filename: str | None = None,
    content_type: str | None = None,
    ip: str = "127.0.0.1",
) -> ActivationRequest:
    """Verify signatory identity, store authorisation letter, and submit claim to AICTE queue.

    Spec 11:
    3. Signatory verified: mock DigiLocker check plus uploaded authorisation letter.
    4. The request goes into the AICTE approval queue.
    """
    token_data = decode_activation_token(payload.activation_token)
    institution_id = int(token_data["institution_id"])
    inst = db.get(Institution, institution_id)
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

    if inst.account_status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Institution is already activated",
        )

    if inst.approval_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Institution approval status is '{inst.approval_status}'",
        )

    # Check for existing pending request
    pending = db.scalar(
        select(ActivationRequest).where(
            ActivationRequest.institution_id == inst.id,
            ActivationRequest.status == "pending",
        )
    )
    if pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An activation claim is already pending approval by AICTE",
        )

    # 1. Signatory identity verification via IdentityVerifier interface
    identity_verifier = get_identity_verifier()
    verif_result = identity_verifier.verify_signatory(
        name=payload.signatory_name,
        signatory_ref=payload.signatory_ref,
        institution_aicte_id=inst.aicte_id,
    )
    if not verif_result.verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Signatory identity verification failed: {verif_result.details}",
        )

    # 2. Store authorisation letter document
    if file_bytes:
        raw_bytes = file_bytes
        fn = filename or "authorisation_letter.pdf"
        ct = content_type or "application/pdf"
    elif payload.letter_content_b64:
        try:
            raw_bytes = base64.b64decode(payload.letter_content_b64)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 encoding for letter document",
            ) from exc
        fn = payload.letter_filename or "authorisation_letter.pdf"
        ct = "application/pdf"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorisation letter document is required",
        )

    storage = get_storage()
    clean_fn = fn.replace(" ", "_")
    storage_path = f"authorisation_letters/{inst.aicte_id}_{uuid.uuid4().hex[:8]}_{clean_fn}"
    letter_ref = storage.save(storage_path, raw_bytes, ct)

    # 3. Create pending activation request
    activation_req = ActivationRequest(
        institution_id=inst.id,
        signatory_name=payload.signatory_name.strip(),
        signatory_ref=verif_result.reference_id or payload.signatory_ref.strip(),
        letter_ref=letter_ref,
        status="pending",
    )
    db.add(activation_req)
    inst.account_status = "pending_approval"
    db.flush()

    audit_service.record(
        db=db,
        action="institution.activation_requested",
        actor_id=inst.aicte_id,
        actor_role="anonymous",
        entity="activation_requests",
        entity_id=activation_req.id,
        before_json={"account_status": "not_activated"},
        after_json={
            "institution_id": inst.id,
            "aicte_id": inst.aicte_id,
            "signatory_name": activation_req.signatory_name,
            "signatory_ref": activation_req.signatory_ref,
            "letter_ref": activation_req.letter_ref,
            "status": "pending",
            "account_status": "pending_approval",
        },
        ip=ip,
    )

    # 5. Send transactional notification to AICTE queue
    otp_sender = get_otp_sender(db)
    otp_sender.send_notification(
        channel="email",
        recipient="approvals@aicte-india.org",
        body=(
            f"New college activation request #{activation_req.id} submitted for "
            f"{inst.aicte_id} - {inst.name} by signatory {activation_req.signatory_name}."
        ),
    )

    db.commit()
    db.refresh(activation_req)
    return activation_req


def list_activation_requests(
    db: Session,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[ActivationRequest]]:
    """List activation requests with optional status filtering for AICTE officers."""
    query = select(ActivationRequest).options(selectinload(ActivationRequest.institution))
    if status_filter:
        query = query.where(ActivationRequest.status == status_filter)

    count_query = select(func.count(ActivationRequest.id))
    if status_filter:
        count_query = count_query.where(ActivationRequest.status == status_filter)

    total = db.scalar(count_query) or 0
    items = list(
        db.scalars(
            query.order_by(ActivationRequest.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )
    return total, items


def get_activation_request(db: Session, request_id: int) -> ActivationRequest:
    """Retrieve activation request by ID with institution details."""
    req = db.scalar(
        select(ActivationRequest)
        .options(selectinload(ActivationRequest.institution))
        .where(ActivationRequest.id == request_id)
    )
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activation request {request_id} not found",
        )
    return req


def approve_activation_request(
    db: Session,
    request_id: int,
    current_user: User,
    admin_email: str | None = None,
    notes: str | None = None,
    ip: str = "127.0.0.1",
) -> ActivationDecisionResponse:
    """Approve college activation claim and create primary admin account with MFA.

    Spec 11:
    4. An officer approves or rejects.
    5. On approval the primary admin account is created with MFA enabled.
    """
    req = get_activation_request(db, request_id)
    if req.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Activation request #{request_id} is already '{req.status}'",
        )

    inst = req.institution
    before_req = {"status": req.status}
    before_inst = {"account_status": inst.account_status}

    req.status = "approved"
    req.decided_by = current_user.id
    req.decided_at = datetime.now(UTC)

    inst.account_status = "active"

    # 3. Create or promote primary admin account (Role.COLLEGE_ADMIN)
    target_email = (admin_email or inst.official_email).strip().lower()
    initial_password = f"Admin@{secrets.token_hex(4).upper()}!2026"
    mfa_secret = generate_totp_secret()
    mfa_uri = get_totp_uri(secret=mfa_secret, account_email=target_email)

    admin_user = db.scalar(select(User).where(User.email == target_email))
    if admin_user is None:
        admin_user = User(
            email=target_email,
            password_hash=hash_password(initial_password),
            role=Role.COLLEGE_ADMIN.value,
            institution_id=inst.id,
            mfa_secret=mfa_secret,
            is_active=True,
        )
        db.add(admin_user)
        db.flush()
    else:
        admin_user.role = Role.COLLEGE_ADMIN.value
        admin_user.institution_id = inst.id
        admin_user.is_active = True
        if not admin_user.mfa_secret:
            admin_user.mfa_secret = mfa_secret
        admin_user.password_hash = hash_password(initial_password)
        db.flush()

    audit_service.record(
        db=db,
        action="institution.activation_approved",
        actor_id=current_user.id,
        actor_role=current_user.role,
        entity="activation_requests",
        entity_id=req.id,
        before_json={"request": before_req, "institution": before_inst},
        after_json={
            "request_id": req.id,
            "status": "approved",
            "decided_by": current_user.id,
            "institution_id": inst.id,
            "account_status": "active",
            "admin_user_id": admin_user.id,
            "admin_email": admin_user.email,
            "mfa_enabled": True,
            "notes": notes,
        },
        ip=ip,
    )

    # 5. Send transactional notification with activation confirmation
    otp_sender = get_otp_sender(db)
    otp_sender.send_notification(
        channel="email",
        recipient=target_email,
        body=(
            f"Congratulations! Your college account for '{inst.name}' has been approved by AICTE. "
            f"Your primary administrator email is '{target_email}'. "
            "Please log in and configure your two-factor authentication (MFA)."
        ),
    )

    db.commit()
    db.refresh(req)
    db.refresh(inst)
    db.refresh(admin_user)

    return ActivationDecisionResponse(
        request_id=req.id,
        institution_id=inst.id,
        status="approved",
        institution_account_status="active",
        admin_user_id=admin_user.id,
        admin_email=admin_user.email,
        initial_password=initial_password,
        mfa_enabled=True,
        mfa_secret=mfa_secret,
        mfa_uri=mfa_uri,
        message=(f"Activation #{req.id} approved. Primary admin created for {admin_user.email}."),
    )


def reject_activation_request(
    db: Session,
    request_id: int,
    current_user: User,
    reason: str,
    ip: str = "127.0.0.1",
) -> ActivationDecisionResponse:
    """Reject college activation claim with stated reason."""
    req = get_activation_request(db, request_id)
    if req.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Activation request #{request_id} is already '{req.status}'",
        )

    inst = req.institution
    before_req = {"status": req.status}
    before_inst = {"account_status": inst.account_status}

    req.status = "rejected"
    req.decided_by = current_user.id
    req.decided_at = datetime.now(UTC)

    inst.account_status = "not_activated"

    audit_service.record(
        db=db,
        action="institution.activation_rejected",
        actor_id=current_user.id,
        actor_role=current_user.role,
        entity="activation_requests",
        entity_id=req.id,
        before_json={"request": before_req, "institution": before_inst},
        after_json={
            "request_id": req.id,
            "status": "rejected",
            "reason": reason,
            "decided_by": current_user.id,
            "institution_id": inst.id,
            "account_status": "not_activated",
        },
        ip=ip,
    )

    # 4. Dispatch notification
    otp_sender = get_otp_sender(db)
    otp_sender.send_notification(
        channel="email",
        recipient=inst.official_email,
        body=(
            f"Your activation request for '{inst.name}' ({inst.aicte_id}) was rejected by AICTE. "
            f"Reason: {reason}"
        ),
    )

    db.commit()
    db.refresh(req)
    db.refresh(inst)

    return ActivationDecisionResponse(
        request_id=req.id,
        institution_id=inst.id,
        status="rejected",
        institution_account_status="not_activated",
        admin_user_id=None,
        admin_email=None,
        initial_password=None,
        mfa_enabled=False,
        mfa_secret=None,
        mfa_uri=None,
        message=f"Activation request #{req.id} rejected.",
    )


def get_activation_status(db: Session, aicte_id: str) -> ActivationStatusResponse:
    """Public query to check current activation state of an institution."""
    cleaned_id = aicte_id.strip()
    inst = db.scalar(select(Institution).where(Institution.aicte_id == cleaned_id))
    if not inst:
        master_client = get_aicte_master_client()
        master_record = master_client.get_institution(cleaned_id)
        if not master_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Institution ID '{cleaned_id}' not found in official AICTE registry",
            )
        return ActivationStatusResponse(
            aicte_id=master_record.aicte_id,
            institution_name=master_record.name,
            account_status="not_activated",
            approval_status=master_record.approval_status,
            has_pending_request=False,
            latest_request_status=None,
            latest_request_id=None,
        )

    latest_req = db.scalar(
        select(ActivationRequest)
        .where(ActivationRequest.institution_id == inst.id)
        .order_by(ActivationRequest.created_at.desc())
    )

    has_pending = latest_req is not None and latest_req.status == "pending"

    return ActivationStatusResponse(
        aicte_id=inst.aicte_id,
        institution_name=inst.name,
        account_status=inst.account_status,
        approval_status=inst.approval_status,
        has_pending_request=has_pending,
        latest_request_status=latest_req.status if latest_req else None,
        latest_request_id=latest_req.id if latest_req else None,
    )


# Staff Management (Spec 5, 6, 11, TASKS.md T09)


def create_staff(
    db: Session,
    institution_id: int,
    payload: StaffCreateRequest,
    current_user: User,
    ip: str | None = None,
) -> User:
    """College admin creates a new staff user with limited roles.

    Spec 5 & 11:
    - college_admin creates staff with roles (college_staff, college_viewer, college_admin).
    - staff cannot manage staff (role limit).
    """
    inst = get_institution(db, institution_id)
    if inst.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot add staff: Institution account is not active",
        )

    clean_email = payload.email.lower().strip()

    # Email uniqueness check
    existing = db.scalar(select(User).where(User.email == clean_email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{clean_email}' already exists",
        )

    # Role validation: only college roles allowed
    if payload.role not in Role.college_roles():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid staff role '{payload.role}'. "
                f"Must be one of: {', '.join(Role.college_roles())}"
            ),
        )

    new_user = User(
        email=clean_email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        institution_id=institution_id,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    audit_service.record(
        db=db,
        action="staff.create",
        actor_id=current_user.id,
        actor_role=current_user.role,
        entity="users",
        entity_id=new_user.id,
        before_json=None,
        after_json={
            "email": new_user.email,
            "role": new_user.role,
            "institution_id": institution_id,
            "is_active": new_user.is_active,
        },
        ip=ip,
    )

    return new_user


def list_staff(
    db: Session,
    institution_id: int,
    role: str | None = None,
    is_active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[User]]:
    """List staff members of an institution with optional filtering and pagination."""
    get_institution(db, institution_id)
    query = select(User).where(User.institution_id == institution_id)

    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    staff_members = list(
        db.scalars(query.order_by(User.created_at.desc()).limit(limit).offset(offset)).all()
    )
    return total, staff_members


def get_staff(
    db: Session,
    institution_id: int,
    user_id: int,
) -> User:
    """Retrieve a single staff member of an institution."""
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.institution_id == institution_id,
        )
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff user with ID {user_id} not found in institution {institution_id}",
        )
    return user


def update_staff(
    db: Session,
    institution_id: int,
    user_id: int,
    payload: StaffUpdateRequest,
    current_user: User,
    ip: str | None = None,
) -> User:
    """Update a staff member's role, status, or password."""
    user = get_staff(db, institution_id, user_id)

    # Self-deactivation prevention
    if payload.is_active is False and current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    # Role validation
    if payload.role is not None:
        if payload.role not in Role.college_roles():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid staff role '{payload.role}'",
            )
        # Prevent self role downgrade if sole admin
        if user_id == current_user.id and payload.role != Role.COLLEGE_ADMIN.value:
            admin_count = (
                db.scalar(
                    select(func.count()).where(
                        User.institution_id == institution_id,
                        User.role == Role.COLLEGE_ADMIN.value,
                        User.is_active.is_(True),
                    )
                )
                or 0
            )
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Cannot downgrade role: institution must have "
                        "at least one active college_admin"
                    ),
                )

    before_state = {
        "role": user.role,
        "is_active": user.is_active,
    }

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)

    db.commit()
    db.refresh(user)

    after_state = {
        "role": user.role,
        "is_active": user.is_active,
    }

    audit_service.record(
        db=db,
        action="staff.update",
        actor_id=current_user.id,
        actor_role=current_user.role,
        entity="users",
        entity_id=user.id,
        before_json=before_state,
        after_json=after_state,
        ip=ip,
    )

    return user


def delete_staff(
    db: Session,
    institution_id: int,
    user_id: int,
    current_user: User,
    ip: str | None = None,
) -> None:
    """Deactivate a staff member from an institution."""
    user = get_staff(db, institution_id, user_id)

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete or deactivate your own account",
        )

    before_state = {
        "role": user.role,
        "is_active": user.is_active,
    }

    user.is_active = False
    db.commit()

    audit_service.record(
        db=db,
        action="staff.deactivate",
        actor_id=current_user.id,
        actor_role=current_user.role,
        entity="users",
        entity_id=user.id,
        before_json=before_state,
        after_json={"role": user.role, "is_active": False},
        ip=ip,
    )


# Contact or Head Change Requests (Spec 6, 11)


def create_contact_change_request(
    db: Session,
    institution_id: int,
    payload: ContactChangeRequestCreate,
    current_user: User,
    ip: str | None = None,
) -> CorrectionRequest:
    """Create a formal contact or head change request to AICTE.

    Spec 6 & 11:
    - Official email, phone, head of institution: AICTE-owned.
    - College requests a change, AICTE approves. Never self-service.
    """
    inst = get_institution(db, institution_id)

    data: dict[str, Any] = {"reason": payload.reason}
    has_contact = False

    if payload.official_email:
        data["official_email"] = payload.official_email
        has_contact = True
    if payload.official_phone:
        data["official_phone"] = payload.official_phone
        has_contact = True
    if payload.head_name:
        data["head_name"] = payload.head_name
        has_contact = True
    if payload.address:
        data["address"] = payload.address
        has_contact = True

    if not has_contact:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "At least one field to change (official_email, official_phone, "
                "head_name, address) must be provided"
            ),
        )

    data["current_values"] = {
        "official_email": inst.official_email,
        "official_phone": inst.official_phone,
        "head_name": inst.head_name,
        "address": inst.address,
    }

    req_create = CorrectionRequestCreate(
        kind="contact_change",
        payload_json=data,
    )

    return create_correction_request(
        db=db,
        institution_id=institution_id,
        payload=req_create,
        user=current_user,
        ip=ip,
    )
