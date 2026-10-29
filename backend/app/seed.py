"""Database seed script and demo data generator."""

import csv
import random
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.integrations.mock.aicte_master import _build_default_30_colleges
from app.models import (
    ConsentRequest,
    Course,
    CourseIntake,
    Institution,
    Justification,
    MockApaarRegistry,
    ReviewItem,
    SeatDeclaration,
    Student,
    Submission,
    User,
    ValidationFlag,
    VerifiedRecord,
    Verifier,
)

settings = get_settings()
ph = PasswordHasher()
fernet = Fernet(settings.FERNET_KEY.encode())
fake = Faker("en_IN")

DEMO_DIR = Path(__file__).resolve().parent.parent.parent / "demo"
DEMO_PASSWORD = "Demo@12345"


def encrypt_dob(d: date) -> str:
    """Encrypt date of birth using Fernet key."""
    return fernet.encrypt(d.isoformat().encode()).decode()


def decrypt_dob(encrypted: str) -> date:
    """Decrypt date of birth using Fernet key."""
    return date.fromisoformat(fernet.decrypt(encrypted.encode()).decode())


def seed_institutions_and_courses(
    session: Session,
) -> tuple[dict[str, Institution], dict[tuple[int, str], Course]]:
    """Seed the canonical 30 AICTE institutions, their courses, and intake."""
    master_colleges = _build_default_30_colleges()

    # Pre-fetch existing institutions and courses
    existing_insts = {inst.aicte_id: inst for inst in session.scalars(select(Institution)).all()}

    inst_map: dict[str, Institution] = {}
    inst_idx = 0

    for aicte_id, info in master_colleges.items():
        inst_idx += 1
        # Determine account status: first 20 active, next 5 pending, next 5 not_activated
        if inst_idx <= 20:
            account_status = "active"
        elif inst_idx <= 25:
            account_status = "pending_approval"
        else:
            account_status = "not_activated"

        if aicte_id in existing_insts:
            inst = existing_insts[aicte_id]
            inst.name = info.name
            inst.state = info.state
            inst.district = info.district
            inst.address = info.address
            inst.official_email = info.official_email
            inst.official_phone = info.official_phone
            inst.head_name = info.head_name
            inst.affiliating_university = info.affiliating_university
            inst.approval_status = info.approval_status
            inst.approval_valid_to = info.approval_valid_to
            inst.account_status = account_status
        else:
            inst = Institution(
                aicte_id=aicte_id,
                name=info.name,
                state=info.state,
                district=info.district,
                address=info.address,
                official_email=info.official_email,
                official_phone=info.official_phone,
                head_name=info.head_name,
                affiliating_university=info.affiliating_university,
                approval_status=info.approval_status,
                approval_valid_to=info.approval_valid_to,
                account_status=account_status,
            )
            session.add(inst)
            session.flush()

        inst_map[aicte_id] = inst

    # Seed Courses and Intake
    existing_courses = {
        (c.institution_id, c.name, c.branch, c.level): c
        for c in session.scalars(select(Course)).all()
    }
    course_map: dict[tuple[int, str], Course] = {}

    for aicte_id, info in master_colleges.items():
        inst = inst_map[aicte_id]
        for c_info in info.courses:
            course_key = (inst.id, c_info.name, c_info.branch, c_info.level)
            if course_key in existing_courses:
                course = existing_courses[course_key]
                course.duration_years = c_info.duration_years
                course.supernumerary_allowed = c_info.supernumerary_allowed
            else:
                course = Course(
                    institution_id=inst.id,
                    name=c_info.name,
                    level=c_info.level,
                    branch=c_info.branch,
                    duration_years=c_info.duration_years,
                    supernumerary_allowed=c_info.supernumerary_allowed,
                )
                session.add(course)
                session.flush()

            course_map[(inst.id, course.name)] = course

            # Seed Intake for both 2025-26 and 2026-27
            for year in ["2025-26", "2026-27"]:
                existing_intake = session.scalar(
                    select(CourseIntake).where(
                        CourseIntake.course_id == course.id,
                        CourseIntake.academic_year == year,
                    )
                )
                if not existing_intake:
                    intake = CourseIntake(
                        course_id=course.id,
                        academic_year=year,
                        approved_intake=c_info.approved_intake,
                        supernumerary_seats_allowed=c_info.supernumerary_seats_allowed,
                        source="aicte_master",
                        set_by="aicte_sync",
                    )
                    session.add(intake)

    session.flush()
    return inst_map, course_map


def seed_demo_accounts(session: Session, inst_map: dict[str, Institution]) -> dict[str, User]:
    """Seed the standard demo accounts listed in SPEC.md section 18."""
    password_hash = ph.hash(DEMO_PASSWORD)

    demo_users_spec = [
        # AICTE Central Roles
        ("aicte_admin@aicte-india.org", "aicte_admin", None),
        ("aicte_officer@aicte-india.org", "aicte_officer", None),
        # College Admins at different stages
        ("admin@piaet-pune.edu.in", "college_admin", inst_map["1-10000001"].id),  # Clean
        ("admin@mmit-mumbai.ac.in", "college_admin", inst_map["1-10000002"].id),  # Exceptions
        ("admin@ngec-nagpur.gov.in", "college_admin", inst_map["1-10000003"].id),  # Draft
        # Verifier Account
        ("verifier@tcs-verifications.com", "verifier", None),
    ]

    users_map: dict[str, User] = {}
    for email, role, inst_id in demo_users_spec:
        user = session.scalar(select(User).where(User.email == email))
        if not user:
            user = User(
                email=email,
                password_hash=password_hash,
                role=role,
                institution_id=inst_id,
                is_active=True,
            )
            session.add(user)
            session.flush()
        else:
            user.role = role
            user.institution_id = inst_id
            user.is_active = True
        users_map[email] = user

    # Seed Verifier organization record
    verifier_org = session.scalar(
        select(Verifier).where(Verifier.contact == "verifier@tcs-verifications.com")
    )
    if not verifier_org:
        verifier_org = Verifier(
            org_name="Tata Consultancy Services - Background Verifications",
            org_type="employer",
            contact="verifier@tcs-verifications.com",
            status="approved",
        )
        session.add(verifier_org)
        session.flush()

    return users_map


def seed_mock_apaar_registry(session: Session) -> dict[str, MockApaarRegistry]:
    """Seed the simulated APAAR identity registry (~8,500 entries)."""
    fake.seed_instance(42)
    random.seed(42)

    existing_aids = set(session.scalars(select(MockApaarRegistry.apaar_id)).all())
    to_create: list[MockApaarRegistry] = []

    # 1. Dedicated Demo Student
    if "111122223333" not in existing_aids:
        to_create.append(
            MockApaarRegistry(
                apaar_id="111122223333",
                name="Aarav Sharma",
                dob=date(2004, 5, 15),
                gender="Male",
            )
        )
        existing_aids.add("111122223333")

    # 2. Planted Duplicate Enrolment Student
    if "555566667777" not in existing_aids:
        to_create.append(
            MockApaarRegistry(
                apaar_id="555566667777",
                name="Priya Patel",
                dob=date(2004, 11, 20),
                gender="Female",
            )
        )
        existing_aids.add("555566667777")

    # 3. Planted Sequential APAAR Identities (990000000101 - 990000000112)
    for i in range(101, 113):
        aid = f"990000000{i:03d}"
        if aid not in existing_aids:
            to_create.append(
                MockApaarRegistry(
                    apaar_id=aid,
                    name=fake.name(),
                    dob=date(2004, 8, 10),
                    gender="Male" if i % 2 == 0 else "Female",
                )
            )
            existing_aids.add(aid)

    # 4. Specific identities for messy upload tests
    messy_specific = [
        ("300000000050", "Vikram Malhotra", date(2004, 8, 12), "Male"),
        ("300000000051", "Neha Sharma", date(2004, 6, 10), "Female"),
    ]
    for aid, name, dob, gender in messy_specific:
        if aid not in existing_aids:
            to_create.append(
                MockApaarRegistry(
                    apaar_id=aid,
                    name=name,
                    dob=dob,
                    gender=gender,
                )
            )
            existing_aids.add(aid)

    # 5. 2025-26 History Identities (100000000001 - 100000003200) -> 3,200 IDs
    for i in range(1, 3201):
        aid = f"1000000{i:05d}"
        if aid not in existing_aids:
            y = random.randint(2002, 2006)
            m = random.randint(1, 12)
            d = random.randint(1, 28)
            to_create.append(
                MockApaarRegistry(
                    apaar_id=aid,
                    name=fake.name(),
                    dob=date(y, m, d),
                    gender="Male" if i % 2 == 0 else "Female",
                )
            )
            existing_aids.add(aid)

    # 6. 2026-27 Students (200000000001 - 200000002000) -> 2,000 IDs
    for i in range(1, 2001):
        aid = f"2000000{i:05d}"
        if aid not in existing_aids:
            y = random.randint(2003, 2007)
            m = random.randint(1, 12)
            d = random.randint(1, 28)
            to_create.append(
                MockApaarRegistry(
                    apaar_id=aid,
                    name=fake.name(),
                    dob=date(y, m, d),
                    gender="Female" if i % 2 == 0 else "Male",
                )
            )
            existing_aids.add(aid)

    # 7. Unassigned Registry Pool for Uploads & Tests (300000000001 - 300000004000) -> 4,000 IDs
    for i in range(1, 4001):
        aid = f"3000000{i:05d}"
        if aid not in existing_aids:
            y = random.randint(2003, 2007)
            m = random.randint(1, 12)
            d = random.randint(1, 28)
            to_create.append(
                MockApaarRegistry(
                    apaar_id=aid,
                    name=fake.name(),
                    dob=date(y, m, d),
                    gender="Male" if i % 2 == 0 else "Female",
                )
            )
            existing_aids.add(aid)

    if to_create:
        session.bulk_save_objects(to_create)
        session.flush()

    return {reg.apaar_id: reg for reg in session.scalars(select(MockApaarRegistry)).all()}


def seed_2025_26_history(
    session: Session,
    inst_map: dict[str, Institution],
    registry: dict[str, MockApaarRegistry],
) -> int:
    """Seed academic year 2025-26 as accepted history (~3,000 students).

    Spans Colleges 1 through 15 across all their 45 approved courses.
    Admitted counts are ~66.7% of approved intake (regular <= approved_intake),
    producing EXACTLY 3,000 valid student records with zero validation errors.
    """
    random.seed(42)
    colleges_2025 = [inst_map[f"1-100000{i:02d}"] for i in range(1, 16)]
    existing_students = {
        (s.institution_id, s.academic_year, s.apaar_id)
        for s in session.scalars(select(Student).where(Student.academic_year == "2025-26")).all()
    }

    students_to_insert: list[Student] = []
    apaar_counter = 1

    # First student in College 1 CSE is dedicated demo student Aarav Sharma (111122223333)
    demo_student_seeded = False

    total_created = 0

    for inst in colleges_2025:
        # Check or create submission
        sub = session.scalar(
            select(Submission).where(
                Submission.institution_id == inst.id,
                Submission.academic_year == "2025-26",
            )
        )
        if not sub:
            sub = Submission(
                institution_id=inst.id,
                academic_year="2025-26",
                status="accepted",
                receipt_no=f"REC-202526-{inst.aicte_id}",
                submitted_at=datetime(2025, 10, 15, 14, 30, tzinfo=UTC),
            )
            session.add(sub)
            session.flush()

        # Iterate over approved courses
        courses = session.scalars(
            select(Course).where(Course.institution_id == inst.id).order_by(Course.id)
        ).all()

        for course in courses:
            intake = session.scalar(
                select(CourseIntake).where(
                    CourseIntake.course_id == course.id,
                    CourseIntake.academic_year == "2025-26",
                )
            )
            approved_intake = intake.approved_intake if intake else 60

            # Admitted: exactly 2/3 of intake (40 for 60, 80 for 120, 120 for 180)
            target_admitted = (approved_intake * 2) // 3
            super_count = 2 if (course.supernumerary_allowed and target_admitted > 30) else 0
            regular_count = target_admitted - super_count

            # Seat Declaration
            decl = session.scalar(
                select(SeatDeclaration).where(
                    SeatDeclaration.course_id == course.id,
                    SeatDeclaration.academic_year == "2025-26",
                )
            )
            if not decl:
                decl = SeatDeclaration(
                    course_id=course.id,
                    academic_year="2025-26",
                    regular_admitted=regular_count,
                    supernumerary_admitted=super_count,
                    nri_count=0,
                    oci_count=0,
                    fn_count=0,
                    status="locked",
                )
                session.add(decl)

            # Generate students for this course
            for s_idx in range(1, target_admitted + 1):
                if (
                    not demo_student_seeded
                    and inst.aicte_id == "1-10000001"
                    and "Computer Science" in course.name
                ):
                    aid = "111122223333"
                    demo_student_seeded = True
                else:
                    aid = f"1000000{apaar_counter:05d}"
                    apaar_counter += 1

                reg_entry = registry.get(aid)
                if not reg_entry:
                    continue

                if (inst.id, "2025-26", aid) in existing_students:
                    continue

                seat_type = "Supernumerary" if s_idx <= super_count else "Regular"
                admission_date = date(2025, 7, 1 + (s_idx % 25))
                adm_mode = "JEE Main counselling" if s_idx % 2 == 0 else "State counselling"

                student = Student(
                    institution_id=inst.id,
                    course_id=course.id,
                    academic_year="2025-26",
                    apaar_id=aid,
                    name=reg_entry.name,
                    dob_encrypted=encrypt_dob(reg_entry.dob),
                    gender=reg_entry.gender,
                    enrolment_no=f"EN25-{course.id:03d}-{s_idx:04d}",
                    admission_date=admission_date,
                    admission_mode=adm_mode,
                    seat_type=seat_type,
                    reservation_category=["General", "OBC", "SC", "ST", "EWS"][s_idx % 5],
                    nri="No",
                    oci="No",
                    foreign_national="No",
                    fn_country=None,
                    status="submitted",
                    is_locked=True,
                    submission_id=sub.id,
                    source="csv",
                )
                students_to_insert.append(student)
                existing_students.add((inst.id, "2025-26", aid))
                total_created += 1

    if students_to_insert:
        session.add_all(students_to_insert)
        session.flush()

    # Link demo student verified record and consent
    demo_student = session.scalar(
        select(Student).where(
            Student.academic_year == "2025-26",
            Student.apaar_id == "111122223333",
        )
    )
    if demo_student:
        vr = session.scalar(
            select(VerifiedRecord).where(VerifiedRecord.student_id == demo_student.id)
        )
        if not vr or (vr and vr.signature.startswith("MOCK")):
            from app.verification.signing import build_canonical_payload, sign_payload

            inst_name = (
                demo_student.institution.name
                if demo_student.institution
                else "Pune Institute of Advanced Engineering & Technology"
            )
            course_name = (
                demo_student.course.name
                if demo_student.course
                else "B.Tech in Computer Engineering"
            )
            seed_issued_at = datetime(2025, 11, 1, 10, 0, tzinfo=UTC)
            seed_vid = "VR-2025-111122223333"
            seed_payload = build_canonical_payload(
                verification_id=seed_vid,
                apaar_id=demo_student.apaar_id,
                institution=inst_name,
                course=course_name,
                years=demo_student.academic_year,
                status=demo_student.status,
                issued_at=seed_issued_at,
            )
            seed_sig = sign_payload(seed_payload)
            if not vr:
                vr = VerifiedRecord(
                    student_id=demo_student.id,
                    verification_id=seed_vid,
                    signature=seed_sig,
                    issued_at=seed_issued_at,
                    status="active",
                )
                session.add(vr)
            else:
                vr.verification_id = seed_vid
                vr.signature = seed_sig
                vr.issued_at = seed_issued_at
                vr.status = "active"

        verifier_org = session.scalar(
            select(Verifier).where(Verifier.contact == "verifier@tcs-verifications.com")
        )
        if verifier_org:
            consent = session.scalar(
                select(ConsentRequest).where(
                    ConsentRequest.verifier_id == verifier_org.id,
                    ConsentRequest.apaar_id == "111122223333",
                )
            )
            if not consent:
                consent = ConsentRequest(
                    verifier_id=verifier_org.id,
                    apaar_id="111122223333",
                    scope_json={"fields": ["institution", "course", "academic_year", "status"]},
                    status="approved",
                    requested_at=datetime.now(UTC) - timedelta(hours=2),
                    decided_at=datetime.now(UTC) - timedelta(hours=1),
                    expires_at=datetime.now(UTC) + timedelta(hours=22),
                )
                session.add(consent)

    # Seed dedicated tampered record for demo verification (VR-TAMPERED-DEMO)
    tampered_student = session.scalar(
        select(Student).where(
            Student.academic_year == "2025-26",
            Student.apaar_id == "100000000001",
        )
    )
    if tampered_student:
        vr_tampered = session.scalar(
            select(VerifiedRecord).where(VerifiedRecord.verification_id == "VR-TAMPERED-DEMO")
        )
        if not vr_tampered:
            vr_tampered = VerifiedRecord(
                student_id=tampered_student.id,
                verification_id="VR-TAMPERED-DEMO",
                signature="0" * 128,  # Invalid signature causing mismatch
                issued_at=datetime(2025, 11, 1, 10, 0, tzinfo=UTC),
                status="active",
            )
            session.add(vr_tampered)
        else:
            vr_tampered.signature = "0" * 128
            vr_tampered.status = "active"

    session.flush()
    return total_created


def seed_2026_27_mixed_states(
    session: Session,
    inst_map: dict[str, Institution],
    registry: dict[str, MockApaarRegistry],
    demo_users: dict[str, User],
) -> int:
    """Seed academic year 2026-27 with mixed states and planted anomalies."""
    existing_students = {
        (s.institution_id, s.academic_year, s.apaar_id)
        for s in session.scalars(select(Student).where(Student.academic_year == "2026-27")).all()
    }

    students_to_insert: list[Student] = []
    apaar_counter = 1
    total_created = 0

    # 1. College 1 (Pune Institute, 1-10000001): Clean Submitted State
    pune_inst = inst_map["1-10000001"]
    sub1 = session.scalar(
        select(Submission).where(
            Submission.institution_id == pune_inst.id,
            Submission.academic_year == "2026-27",
        )
    )
    if not sub1:
        sub1 = Submission(
            institution_id=pune_inst.id,
            academic_year="2026-27",
            status="submitted",
            receipt_no=f"REC-202627-{pune_inst.aicte_id}",
            submitted_at=datetime(2026, 9, 15, 10, 0, tzinfo=UTC),
            submitted_by=demo_users["admin@piaet-pune.edu.in"].id,
        )
        session.add(sub1)
        session.flush()

    pune_courses = session.scalars(
        select(Course).where(Course.institution_id == pune_inst.id).order_by(Course.id)
    ).all()
    for course in pune_courses:
        decl = session.scalar(
            select(SeatDeclaration).where(
                SeatDeclaration.course_id == course.id,
                SeatDeclaration.academic_year == "2026-27",
            )
        )
        target_count = 50
        if not decl:
            decl = SeatDeclaration(
                course_id=course.id,
                academic_year="2026-27",
                regular_admitted=target_count,
                supernumerary_admitted=0,
                status="locked",
            )
            session.add(decl)

        for s_idx in range(1, target_count + 1):
            aid = f"2000000{apaar_counter:05d}"
            apaar_counter += 1
            reg = registry.get(aid)
            if not reg or (pune_inst.id, "2026-27", aid) in existing_students:
                continue

            student = Student(
                institution_id=pune_inst.id,
                course_id=course.id,
                academic_year="2026-27",
                apaar_id=aid,
                name=reg.name,
                dob_encrypted=encrypt_dob(reg.dob),
                gender=reg.gender,
                enrolment_no=f"EN26-PUNE-{course.id:03d}-{s_idx:04d}",
                admission_date=date(2026, 7, 10),
                admission_mode="JEE Main counselling",
                seat_type="Regular",
                reservation_category="General",
                status="submitted",
                is_locked=True,
                submission_id=sub1.id,
                source="form",
            )
            students_to_insert.append(student)
            existing_students.add((pune_inst.id, "2026-27", aid))
            total_created += 1

    # 2. Planted Duplicate Enrolment in College 1 and College 2 (Priya Patel, 555566667777)
    priya_reg = registry["555566667777"]
    if (pune_inst.id, "2026-27", "555566667777") not in existing_students:
        cse_course = pune_courses[0]
        pune_dupe_student = Student(
            institution_id=pune_inst.id,
            course_id=cse_course.id,
            academic_year="2026-27",
            apaar_id="555566667777",
            name=priya_reg.name,
            dob_encrypted=encrypt_dob(priya_reg.dob),
            gender=priya_reg.gender,
            enrolment_no="EN26-PUNE-CSE-DUPE",
            admission_date=date(2026, 7, 12),
            admission_mode="State counselling",
            seat_type="Regular",
            reservation_category="OBC",
            status="submitted",
            is_locked=True,
            submission_id=sub1.id,
            source="csv",
        )
        session.add(pune_dupe_student)
        session.flush()
        existing_students.add((pune_inst.id, "2026-27", "555566667777"))
        total_created += 1

        # Plant warning flag on College 1
        flag1 = ValidationFlag(
            student_id=pune_dupe_student.id,
            course_id=cse_course.id,
            submission_id=sub1.id,
            rule_code="DUP_ACTIVE_OTHER_COLLEGE",
            level="warning",
            field="apaar_id",
            message=(
                "APAAR ID 555566667777 is also active at Mumbai Metropolitan Institute "
                "of Technology (1-10000002) for academic year 2026-27."
            ),
            fix_hint="Verify student enrolment status with the affiliating university.",
            audience="both",
            requires_justification=False,
            status="open",
        )
        session.add(flag1)

    # 3. College 2 (Mumbai Metropolitan, 1-10000002): Submitted with Exceptions (Over-intake & Dupe)
    mumbai_inst = inst_map["1-10000002"]
    sub2 = session.scalar(
        select(Submission).where(
            Submission.institution_id == mumbai_inst.id,
            Submission.academic_year == "2026-27",
        )
    )
    if not sub2:
        sub2 = Submission(
            institution_id=mumbai_inst.id,
            academic_year="2026-27",
            status="submitted_with_exceptions",
            receipt_no=f"REC-202627-{mumbai_inst.aicte_id}",
            submitted_at=datetime(2026, 9, 20, 14, 0, tzinfo=UTC),
            submitted_by=demo_users["admin@mmit-mumbai.ac.in"].id,
        )
        session.add(sub2)
        session.flush()

    mumbai_courses = session.scalars(
        select(Course).where(Course.institution_id == mumbai_inst.id).order_by(Course.id)
    ).all()

    # Plant Priya Patel in Mumbai IT course as duplicate
    it_course = mumbai_courses[0]
    if (mumbai_inst.id, "2026-27", "555566667777") not in existing_students:
        mumbai_dupe_student = Student(
            institution_id=mumbai_inst.id,
            course_id=it_course.id,
            academic_year="2026-27",
            apaar_id="555566667777",
            name=priya_reg.name,
            dob_encrypted=encrypt_dob(priya_reg.dob),
            gender=priya_reg.gender,
            enrolment_no="EN26-MMIT-IT-DUPE",
            admission_date=date(2026, 7, 14),
            admission_mode="Management quota",
            seat_type="Regular",
            reservation_category="OBC",
            status="submitted",
            is_locked=True,
            submission_id=sub2.id,
            source="csv",
        )
        session.add(mumbai_dupe_student)
        session.flush()
        existing_students.add((mumbai_inst.id, "2026-27", "555566667777"))
        total_created += 1

        flag2 = ValidationFlag(
            student_id=mumbai_dupe_student.id,
            course_id=it_course.id,
            submission_id=sub2.id,
            rule_code="DUP_ACTIVE_OTHER_COLLEGE",
            level="warning",
            field="apaar_id",
            message=(
                "APAAR ID 555566667777 is also active at Pune Institute of Advanced "
                "Engineering & Technology (1-10000001) for academic year 2026-27."
            ),
            fix_hint="Verify student enrolment status with the affiliating university.",
            audience="both",
            requires_justification=False,
            status="open",
        )
        session.add(flag2)

    # Over-intake in Mumbai: Data Science & Business Analytics
    # (course 3, approved intake is 60, regular admitted is 68)
    ds_course = [c for c in mumbai_courses if "Data Science" in c.name][0]
    decl2 = session.scalar(
        select(SeatDeclaration).where(
            SeatDeclaration.course_id == ds_course.id,
            SeatDeclaration.academic_year == "2026-27",
        )
    )
    if not decl2:
        decl2 = SeatDeclaration(
            course_id=ds_course.id,
            academic_year="2026-27",
            regular_admitted=68,
            supernumerary_admitted=0,
            status="declared",
        )
        session.add(decl2)

    for s_idx in range(1, 69):
        aid = f"2000000{apaar_counter:05d}"
        apaar_counter += 1
        reg = registry.get(aid)
        if not reg or (mumbai_inst.id, "2026-27", aid) in existing_students:
            continue

        student = Student(
            institution_id=mumbai_inst.id,
            course_id=ds_course.id,
            academic_year="2026-27",
            apaar_id=aid,
            name=reg.name,
            dob_encrypted=encrypt_dob(reg.dob),
            gender=reg.gender,
            enrolment_no=f"EN26-MMIT-DS-{s_idx:04d}",
            admission_date=date(2026, 7, 20),
            admission_mode="State counselling",
            seat_type="Regular",
            reservation_category="General",
            status="submitted",
            is_locked=True,
            submission_id=sub2.id,
            source="csv",
        )
        students_to_insert.append(student)
        existing_students.add((mumbai_inst.id, "2026-27", aid))
        total_created += 1

    # Plant INTAKE_EXCEEDED flag and justification
    flag_over = session.scalar(
        select(ValidationFlag).where(
            ValidationFlag.submission_id == sub2.id,
            ValidationFlag.rule_code == "INTAKE_EXCEEDED",
        )
    )
    if not flag_over:
        flag_over = ValidationFlag(
            course_id=ds_course.id,
            submission_id=sub2.id,
            rule_code="INTAKE_EXCEEDED",
            level="exception",
            field="regular_admitted",
            message="Regular admitted count (68) exceeds approved intake (60) by 8 students.",
            fix_hint=(
                "Provide AICTE approval letter or court order justification for excess admissions."
            ),
            audience="both",
            requires_justification=True,
            status="justified",
        )
        session.add(flag_over)
        session.flush()

        # Add justification
        justification = Justification(
            flag_id=flag_over.id,
            text=(
                "Approved court order AICTE/WP/2026/89 allowing 8 additional seats "
                "for special merit category."
            ),
            document_ref="storage/uploads/justifications/court_order_wp2026_89.pdf",
            by_user=demo_users["admin@mmit-mumbai.ac.in"].id,
            at=datetime(2026, 9, 20, 13, 45, tzinfo=UTC),
        )
        session.add(justification)

        # Add Review Item
        review_item = ReviewItem(
            submission_id=sub2.id,
            flag_ids=[flag_over.id],
            status="under_review",
            assigned_to=demo_users["aicte_officer@aicte-india.org"].id,
        )
        session.add(review_item)

    # 4. College 3 (Nagpur Government, 1-10000003): In Draft State
    nagpur_inst = inst_map["1-10000003"]
    sub3 = session.scalar(
        select(Submission).where(
            Submission.institution_id == nagpur_inst.id,
            Submission.academic_year == "2026-27",
        )
    )
    if not sub3:
        sub3 = Submission(
            institution_id=nagpur_inst.id,
            academic_year="2026-27",
            status="draft",
            submitted_by=None,
            submitted_at=None,
        )
        session.add(sub3)
        session.flush()

    nagpur_courses = session.scalars(
        select(Course).where(Course.institution_id == nagpur_inst.id).order_by(Course.id)
    ).all()
    for course in nagpur_courses:
        decl = session.scalar(
            select(SeatDeclaration).where(
                SeatDeclaration.course_id == course.id,
                SeatDeclaration.academic_year == "2026-27",
            )
        )
        if not decl:
            decl = SeatDeclaration(
                course_id=course.id,
                academic_year="2026-27",
                regular_admitted=15,
                supernumerary_admitted=0,
                status="draft",
            )
            session.add(decl)

        for s_idx in range(1, 16):
            aid = f"2000000{apaar_counter:05d}"
            apaar_counter += 1
            reg = registry.get(aid)
            if not reg or (nagpur_inst.id, "2026-27", aid) in existing_students:
                continue

            student = Student(
                institution_id=nagpur_inst.id,
                course_id=course.id,
                academic_year="2026-27",
                apaar_id=aid,
                name=reg.name,
                dob_encrypted=encrypt_dob(reg.dob),
                gender=reg.gender,
                enrolment_no=f"EN26-NGEC-{course.id:03d}-{s_idx:04d}",
                admission_date=date(2026, 8, 5),
                admission_mode="State counselling",
                seat_type="Regular",
                reservation_category="General",
                status="draft",
                is_locked=False,
                submission_id=sub3.id,
                source="form",
            )
            students_to_insert.append(student)
            existing_students.add((nagpur_inst.id, "2026-27", aid))
            total_created += 1

    # 5. Planted Anomaly: Sudden Enrolment Jump (College 4 BNITS, 1-10000004)
    # 2025-26 had 120 intake -> 80 students.
    # In 2026-27, enrolment jumped to 160 (+100%, > 30% jump).
    bnits_inst = inst_map["1-10000004"]
    bnits_sub = session.scalar(
        select(Submission).where(
            Submission.institution_id == bnits_inst.id,
            Submission.academic_year == "2026-27",
        )
    )
    if not bnits_sub:
        bnits_sub = Submission(
            institution_id=bnits_inst.id,
            academic_year="2026-27",
            status="submitted",
            receipt_no=f"REC-202627-{bnits_inst.aicte_id}",
            submitted_at=datetime(2026, 9, 18, 11, 0, tzinfo=UTC),
        )
        session.add(bnits_sub)
        session.flush()

    bnits_cse = session.scalars(
        select(Course).where(
            Course.institution_id == bnits_inst.id,
            Course.name.ilike("%Computer Science%"),
        )
    ).first()
    if bnits_cse:
        decl4 = session.scalar(
            select(SeatDeclaration).where(
                SeatDeclaration.course_id == bnits_cse.id,
                SeatDeclaration.academic_year == "2026-27",
            )
        )
        if not decl4:
            decl4 = SeatDeclaration(
                course_id=bnits_cse.id,
                academic_year="2026-27",
                regular_admitted=160,
                supernumerary_admitted=0,
                status="locked",
            )
            session.add(decl4)

        for s_idx in range(1, 161):
            aid = f"2000000{apaar_counter:05d}"
            apaar_counter += 1
            reg = registry.get(aid)
            if not reg or (bnits_inst.id, "2026-27", aid) in existing_students:
                continue

            student = Student(
                institution_id=bnits_inst.id,
                course_id=bnits_cse.id,
                academic_year="2026-27",
                apaar_id=aid,
                name=reg.name,
                dob_encrypted=encrypt_dob(reg.dob),
                gender=reg.gender,
                enrolment_no=f"EN26-BNITS-CSE-{s_idx:04d}",
                admission_date=date(2026, 7, 18),
                admission_mode="JEE Main counselling",
                seat_type="Regular",
                reservation_category="General",
                status="submitted",
                is_locked=True,
                submission_id=bnits_sub.id,
                source="csv",
            )
            students_to_insert.append(student)
            existing_students.add((bnits_inst.id, "2026-27", aid))
            total_created += 1

        flag_jump = session.scalar(
            select(ValidationFlag).where(
                ValidationFlag.submission_id == bnits_sub.id,
                ValidationFlag.rule_code == "ANOM_ENROLMENT_JUMP",
            )
        )
        if not flag_jump:
            flag_jump = ValidationFlag(
                course_id=bnits_cse.id,
                submission_id=bnits_sub.id,
                rule_code="ANOM_ENROLMENT_JUMP",
                level="warning",
                field="enrolment_total",
                message=(
                    "Enrolment jumped from 80 in 2025-26 to 160 in 2026-27 (+100.0%), "
                    "exceeding the 30% threshold."
                ),
                fix_hint="Verify admission register and council approval for intake scaling.",
                audience="aicte",
                requires_justification=False,
                status="open",
            )
            session.add(flag_jump)

    # 6. Planted Anomaly: DOB Cluster (College 5 Mysuru Royal, 1-10000005)
    # 8 students in the same course share the exact DOB 2005-08-15 (threshold 5)
    mysuru_inst = inst_map["1-10000005"]
    mysuru_sub = session.scalar(
        select(Submission).where(
            Submission.institution_id == mysuru_inst.id,
            Submission.academic_year == "2026-27",
        )
    )
    if not mysuru_sub:
        mysuru_sub = Submission(
            institution_id=mysuru_inst.id,
            academic_year="2026-27",
            status="submitted",
            receipt_no=f"REC-202627-{mysuru_inst.aicte_id}",
            submitted_at=datetime(2026, 9, 19, 15, 30, tzinfo=UTC),
        )
        session.add(mysuru_sub)
        session.flush()

    mysuru_mech = session.scalars(
        select(Course).where(Course.institution_id == mysuru_inst.id).order_by(Course.id)
    ).first()
    if mysuru_mech:
        decl5 = session.scalar(
            select(SeatDeclaration).where(
                SeatDeclaration.course_id == mysuru_mech.id,
                SeatDeclaration.academic_year == "2026-27",
            )
        )
        if not decl5:
            decl5 = SeatDeclaration(
                course_id=mysuru_mech.id,
                academic_year="2026-27",
                regular_admitted=40,
                supernumerary_admitted=0,
                status="locked",
            )
            session.add(decl5)

        cluster_dob = date(2005, 8, 15)
        for s_idx in range(1, 41):
            aid = f"2000000{apaar_counter:05d}"
            apaar_counter += 1
            reg = registry.get(aid)
            if not reg or (mysuru_inst.id, "2026-27", aid) in existing_students:
                continue

            # First 8 students share the clustered DOB
            dob_to_use = cluster_dob if s_idx <= 8 else reg.dob

            student = Student(
                institution_id=mysuru_inst.id,
                course_id=mysuru_mech.id,
                academic_year="2026-27",
                apaar_id=aid,
                name=reg.name,
                dob_encrypted=encrypt_dob(dob_to_use),
                gender=reg.gender,
                enrolment_no=f"EN26-MRCE-MECH-{s_idx:04d}",
                admission_date=date(2026, 7, 22),
                admission_mode="State counselling",
                seat_type="Regular",
                reservation_category="General",
                status="submitted",
                is_locked=True,
                submission_id=mysuru_sub.id,
                source="form",
            )
            students_to_insert.append(student)
            existing_students.add((mysuru_inst.id, "2026-27", aid))
            total_created += 1

        flag_cluster = session.scalar(
            select(ValidationFlag).where(
                ValidationFlag.submission_id == mysuru_sub.id,
                ValidationFlag.rule_code == "ANOM_DOB_CLUSTER",
            )
        )
        if not flag_cluster:
            flag_cluster = ValidationFlag(
                course_id=mysuru_mech.id,
                submission_id=mysuru_sub.id,
                rule_code="ANOM_DOB_CLUSTER",
                level="warning",
                field="dob",
                message="Cluster of 8 students sharing the exact date of birth 2005-08-15.",
                fix_hint="Verify identity documentation for date of birth records.",
                audience="aicte",
                requires_justification=False,
                status="open",
            )
            session.add(flag_cluster)

    # 7. Planted Anomaly: Sequential APAAR IDs (College 6 Hubballi, 1-10000006)
    # 12 students with sequential APAAR IDs 990000000101 to 990000000112 (threshold 10)
    hubballi_inst = inst_map["1-10000006"]
    hubballi_sub = session.scalar(
        select(Submission).where(
            Submission.institution_id == hubballi_inst.id,
            Submission.academic_year == "2026-27",
        )
    )
    if not hubballi_sub:
        hubballi_sub = Submission(
            institution_id=hubballi_inst.id,
            academic_year="2026-27",
            status="submitted",
            receipt_no=f"REC-202627-{hubballi_inst.aicte_id}",
            submitted_at=datetime(2026, 9, 21, 16, 0, tzinfo=UTC),
        )
        session.add(hubballi_sub)
        session.flush()

    hubballi_course = session.scalars(
        select(Course).where(Course.institution_id == hubballi_inst.id).order_by(Course.id)
    ).first()
    if hubballi_course:
        decl6 = session.scalar(
            select(SeatDeclaration).where(
                SeatDeclaration.course_id == hubballi_course.id,
                SeatDeclaration.academic_year == "2026-27",
            )
        )
        if not decl6:
            decl6 = SeatDeclaration(
                course_id=hubballi_course.id,
                academic_year="2026-27",
                regular_admitted=30,
                supernumerary_admitted=0,
                status="locked",
            )
            session.add(decl6)

        # First 12 students have sequential APAAR IDs
        for seq_i in range(101, 113):
            aid = f"990000000{seq_i:03d}"
            reg = registry.get(aid)
            if not reg or (hubballi_inst.id, "2026-27", aid) in existing_students:
                continue

            student = Student(
                institution_id=hubballi_inst.id,
                course_id=hubballi_course.id,
                academic_year="2026-27",
                apaar_id=aid,
                name=reg.name,
                dob_encrypted=encrypt_dob(reg.dob),
                gender=reg.gender,
                enrolment_no=f"EN26-HTI-SEQ-{seq_i:04d}",
                admission_date=date(2026, 7, 25),
                admission_mode="State counselling",
                seat_type="Regular",
                reservation_category="General",
                status="submitted",
                is_locked=True,
                submission_id=hubballi_sub.id,
                source="form",
            )
            students_to_insert.append(student)
            existing_students.add((hubballi_inst.id, "2026-27", aid))
            total_created += 1

        flag_seq = session.scalar(
            select(ValidationFlag).where(
                ValidationFlag.submission_id == hubballi_sub.id,
                ValidationFlag.rule_code == "ANOM_SEQUENTIAL_APAAR",
            )
        )
        if not flag_seq:
            flag_seq = ValidationFlag(
                course_id=hubballi_course.id,
                submission_id=hubballi_sub.id,
                rule_code="ANOM_SEQUENTIAL_APAAR",
                level="warning",
                field="apaar_id",
                message="Sequential run of 12 APAAR IDs detected (990000000101 to 990000000112).",
                fix_hint=(
                    "Audit registration logs to rule out bulk automated synthetic "
                    "identity submission."
                ),
                audience="aicte",
                requires_justification=False,
                status="open",
            )
            session.add(flag_seq)

    # 8. Seed additional clean students for other colleges
    # (Colleges 7, 10, 13) to reach realistic totals
    additional_clean = [inst_map[f"1-100000{i:02d}"] for i in [7, 10, 13]]
    for inst in additional_clean:
        sub = session.scalar(
            select(Submission).where(
                Submission.institution_id == inst.id,
                Submission.academic_year == "2026-27",
            )
        )
        if not sub:
            sub = Submission(
                institution_id=inst.id,
                academic_year="2026-27",
                status="submitted",
                receipt_no=f"REC-202627-{inst.aicte_id}",
                submitted_at=datetime(2026, 9, 22, 10, 0, tzinfo=UTC),
            )
            session.add(sub)
            session.flush()

        courses = session.scalars(
            select(Course).where(Course.institution_id == inst.id).order_by(Course.id)
        ).all()
        for course in courses:
            decl = session.scalar(
                select(SeatDeclaration).where(
                    SeatDeclaration.course_id == course.id,
                    SeatDeclaration.academic_year == "2026-27",
                )
            )
            if not decl:
                decl = SeatDeclaration(
                    course_id=course.id,
                    academic_year="2026-27",
                    regular_admitted=40,
                    supernumerary_admitted=0,
                    status="locked",
                )
                session.add(decl)

            for s_idx in range(1, 41):
                aid = f"2000000{apaar_counter:05d}"
                apaar_counter += 1
                reg = registry.get(aid)
                if not reg or (inst.id, "2026-27", aid) in existing_students:
                    continue

                student = Student(
                    institution_id=inst.id,
                    course_id=course.id,
                    academic_year="2026-27",
                    apaar_id=aid,
                    name=reg.name,
                    dob_encrypted=encrypt_dob(reg.dob),
                    gender=reg.gender,
                    enrolment_no=f"EN26-{inst.id:02d}-{course.id:03d}-{s_idx:04d}",
                    admission_date=date(2026, 8, 1),
                    admission_mode="JEE Main counselling",
                    seat_type="Regular",
                    reservation_category="General",
                    status="submitted",
                    is_locked=True,
                    submission_id=sub.id,
                    source="csv",
                )
                students_to_insert.append(student)
                existing_students.add((inst.id, "2026-27", aid))
                total_created += 1

    if students_to_insert:
        session.add_all(students_to_insert)
        session.flush()

    return total_created


def generate_demo_csvs(registry: dict[str, MockApaarRegistry]) -> list[str]:
    """Generate the four demo CSV files in demo/."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    csv_header = [
        "apaar_id",
        "name",
        "dob",
        "gender",
        "course",
        "branch",
        "admission_year",
        "enrolment_no",
        "admission_date",
        "admission_mode",
        "seat_type",
        "reservation_category",
        "nri",
        "oci",
        "foreign_national",
        "country",
    ]

    files_generated = []

    # 1. clean_upload.csv: 25 completely valid student rows
    clean_path = DEMO_DIR / "clean_upload.csv"
    with open(clean_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
        for i in range(1, 26):
            aid = f"3000000{i:05d}"
            reg = registry[aid]
            writer.writerow(
                [
                    aid,
                    reg.name,
                    reg.dob.isoformat(),
                    reg.gender,
                    "Computer Science and Engineering",
                    "Computer Science",
                    "2026-27",
                    f"DEMO-CSE-{i:03d}",
                    "2026-07-15",
                    "JEE Main counselling" if i % 2 == 0 else "State counselling",
                    "Regular",
                    ["General", "OBC", "SC", "ST", "EWS"][i % 5],
                    "No",
                    "No",
                    "No",
                    "",
                ]
            )
    files_generated.append("clean_upload.csv")

    # 2. messy_upload.csv: triggers all 17 row-level rules
    messy_path = DEMO_DIR / "messy_upload.csv"
    with open(messy_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)

        def make_row(
            aid: str = "",
            name: str = "",
            dob: str = "2004-05-10",
            gender: str = "Male",
            course: str = "Computer Science and Engineering",
            branch: str = "Computer Science",
            admission_year: str = "2026-27",
            enrolment_no: str = "MESSY-001",
            admission_date: str = "2026-07-15",
            admission_mode: str = "State counselling",
            seat_type: str = "Regular",
            reservation_category: str = "General",
            nri: str = "No",
            oci: str = "No",
            foreign_national: str = "No",
            country: str = "",
        ) -> list[str]:
            return [
                aid,
                name,
                dob,
                gender,
                course,
                branch,
                admission_year,
                enrolment_no,
                admission_date,
                admission_mode,
                seat_type,
                reservation_category,
                nri,
                oci,
                foreign_national,
                country,
            ]

        messy_rows = [
            # 1. APAAR_REQUIRED: missing APAAR ID
            make_row(aid="", name="Amit Verma", enrolment_no="MESSY-001"),
            # 2. APAAR_FORMAT: 11 digits
            make_row(aid="12345678901", name="Rohan Joshi", enrolment_no="MESSY-002"),
            # 3. NAME_REQUIRED: missing name
            make_row(aid="300000000030", name="", gender="Female", enrolment_no="MESSY-003"),
            # 4. NAME_FORMAT: illegal characters / digits in name
            make_row(aid="300000000031", name="Rahul123 Sharma", enrolment_no="MESSY-004"),
            # 5. DOB_INVALID: future date
            make_row(
                aid="300000000032",
                name="Deepak Gupta",
                dob="2099-01-01",
                enrolment_no="MESSY-005",
            ),
            # 6. ENUM_INVALID: invalid gender and invalid reservation category
            make_row(
                aid="300000000033",
                name="Sunita Nair",
                gender="InvalidGender",
                reservation_category="AlienCategory",
                enrolment_no="MESSY-006",
            ),
            # 7. COUNTRY_REQUIRED: foreign national is Yes but country is empty
            make_row(
                aid="300000000034",
                name="John Smith",
                foreign_national="Yes",
                admission_mode="NRI/OCI/foreign quota",
                enrolment_no="MESSY-007",
            ),
            # 8. ADMISSION_DATE_WINDOW: admission date outside admission window
            make_row(
                aid="300000000035",
                name="Manoj Tiwari",
                admission_date="2026-01-05",
                enrolment_no="MESSY-008",
            ),
            # 9. APAAR_NOT_FOUND: APAAR not in mock registry
            make_row(
                aid="888899990000",
                name="Kiran Rao",
                gender="Female",
                enrolment_no="MESSY-009",
            ),
            # 10. APAAR_NAME_MISMATCH: registry has Vikram Malhotra, upload has Zachary Taylor
            make_row(
                aid="300000000050",
                name="Zachary Taylor",
                dob="2004-08-12",
                enrolment_no="MESSY-010",
            ),
            # 11. APAAR_DOB_MISMATCH: registry has 2004-06-10, upload has 2004-06-11
            make_row(
                aid="300000000051",
                name="Neha Sharma",
                dob="2004-06-11",
                gender="Female",
                enrolment_no="MESSY-011",
            ),
            # 12. CATEGORY_CONFLICT: NRI and foreign_national both Yes
            make_row(
                aid="300000000036",
                name="Tariq Mansoor",
                nri="Yes",
                foreign_national="Yes",
                country="United Arab Emirates",
                admission_mode="NRI/OCI/foreign quota",
                enrolment_no="MESSY-012",
            ),
            # 13. COURSE_NOT_APPROVED: unapproved course/branch for Pune Institute
            make_row(
                aid="300000000037",
                name="Suresh Raina",
                course="Astrophysics & Space Flight",
                branch="Aerospace",
                enrolment_no="MESSY-013",
            ),
            # 14. AGE_OUT_OF_RANGE: UG student born in 1955 (age 71, default range 15-30)
            make_row(
                aid="300000000038",
                name="Govind Prasad",
                dob="1955-03-10",
                enrolment_no="MESSY-014",
            ),
            # 15. SEAT_TYPE_NOT_APPROVED: Supernumerary seat in Mech Engg
            make_row(
                aid="300000000039",
                name="Pooja Hegde",
                gender="Female",
                course="Mechanical Engineering",
                branch="Mechanical",
                seat_type="Supernumerary",
                enrolment_no="MESSY-015",
            ),
            # 16. MODE_CATEGORY_MISMATCH: NRI is Yes, but admission mode is State counselling
            make_row(
                aid="300000000040",
                name="Ananya Singhania",
                gender="Female",
                nri="Yes",
                admission_mode="State counselling",
                enrolment_no="MESSY-016",
            ),
            # 17. ADMISSION_YEAR_MISMATCH: admission_year 2026-27, date 2024-05-10
            make_row(
                aid="300000000041",
                name="Harish Chandra",
                admission_year="2026-27",
                admission_date="2024-05-10",
                enrolment_no="MESSY-017",
            ),
        ]
        for row in messy_rows:
            writer.writerow(row)
    files_generated.append("messy_upload.csv")

    # 3. overintake_upload.csv: 70 regular students for a 60-seat course (Mechanical Engineering)
    over_path = DEMO_DIR / "overintake_upload.csv"
    with open(over_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
        for i in range(101, 171):
            aid = f"3000000{i:05d}"
            reg = registry[aid]
            writer.writerow(
                [
                    aid,
                    reg.name,
                    reg.dob.isoformat(),
                    reg.gender,
                    "Mechanical Engineering",
                    "Mechanical",
                    "2026-27",
                    f"DEMO-MECH-OVER-{i:03d}",
                    "2026-07-20",
                    "State counselling",
                    "Regular",
                    "General",
                    "No",
                    "No",
                    "No",
                    "",
                ]
            )
    files_generated.append("overintake_upload.csv")

    # 4. cross_college_dupe.csv: Contains Priya Patel (555566667777), duplicate of Pune/Mumbai
    dupe_path = DEMO_DIR / "cross_college_dupe.csv"
    with open(dupe_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
        priya = registry["555566667777"]
        writer.writerow(
            [
                priya.apaar_id,
                priya.name,
                priya.dob.isoformat(),
                priya.gender,
                "Civil Engineering",
                "Civil",
                "2026-27",
                "DEMO-NGEC-DUPE-01",
                "2026-08-01",
                "State counselling",
                "Regular",
                "OBC",
                "No",
                "No",
                "No",
                "",
            ]
        )
    files_generated.append("cross_college_dupe.csv")

    return files_generated


def validate_student_record(
    student: Student,
    mock_reg: MockApaarRegistry | None,
    approved_courses: list[Course],
) -> list[str]:
    """Verify a student record against SPEC.md section 9.3 row-level rules.

    Returns a list of error-level violations (if any).
    """
    errors: list[str] = []

    # APAAR_REQUIRED & APAAR_FORMAT
    if not student.apaar_id:
        errors.append("APAAR_REQUIRED")
    elif len(student.apaar_id) != 12 or not student.apaar_id.isdigit():
        errors.append("APAAR_FORMAT")

    # NAME_REQUIRED & NAME_FORMAT
    if not student.name or not student.name.strip():
        errors.append("NAME_REQUIRED")
    elif any(char.isdigit() for char in student.name):
        errors.append("NAME_FORMAT")

    # DOB validation
    try:
        decrypted_dob = decrypt_dob(student.dob_encrypted)
        if decrypted_dob > date.today():
            errors.append("DOB_INVALID")
    except Exception:
        errors.append("DOB_INVALID")

    # ENUM_INVALID
    if student.gender not in ["Male", "Female", "Other"]:
        errors.append("ENUM_INVALID: gender")
    if student.seat_type not in ["Regular", "Supernumerary"]:
        errors.append("ENUM_INVALID: seat_type")
    if student.reservation_category not in ["General", "OBC", "SC", "ST", "EWS"]:
        errors.append("ENUM_INVALID: reservation_category")
    if (
        student.nri not in ["Yes", "No"]
        or student.oci not in ["Yes", "No"]
        or student.foreign_national not in ["Yes", "No"]
    ):
        errors.append("ENUM_INVALID: boolean flags")

    # COUNTRY_REQUIRED
    if student.foreign_national == "Yes" and not student.fn_country:
        errors.append("COUNTRY_REQUIRED")

    # CATEGORY_CONFLICT
    if student.nri == "Yes" and student.foreign_national == "Yes":
        errors.append("CATEGORY_CONFLICT")

    # APAAR_NOT_FOUND & APAAR_DOB_MISMATCH
    if mock_reg is None:
        errors.append("APAAR_NOT_FOUND")
    else:
        try:
            if decrypt_dob(student.dob_encrypted) != mock_reg.dob:
                errors.append("APAAR_DOB_MISMATCH")
        except Exception:
            errors.append("APAAR_DOB_MISMATCH")

    # COURSE_NOT_APPROVED
    matching_course = next((c for c in approved_courses if c.id == student.course_id), None)
    if matching_course is None:
        errors.append("COURSE_NOT_APPROVED")
    else:
        # SEAT_TYPE_NOT_APPROVED
        if student.seat_type == "Supernumerary" and not matching_course.supernumerary_allowed:
            errors.append("SEAT_TYPE_NOT_APPROVED")

    return errors


def seed_all(session: Session | None = None) -> dict[str, Any]:
    """Execute complete seeding process and report counts."""
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    try:
        print("-> Seeding institutions and courses...")
        inst_map, _ = seed_institutions_and_courses(session)

        print("-> Seeding demo accounts and verifier organizations...")
        demo_users = seed_demo_accounts(session, inst_map)

        print("-> Seeding simulated Mock APAAR Registry identities...")
        registry = seed_mock_apaar_registry(session)

        print("-> Seeding 2025-26 accepted history (~3,000 students)...")
        seed_2025_26_history(session, inst_map, registry)

        print("-> Seeding 2026-27 mixed states, planted anomalies and submissions...")
        seed_2026_27_mixed_states(session, inst_map, registry, demo_users)

        print("-> Generating demo CSV files in demo/...")
        demo_csvs = generate_demo_csvs(registry)

        session.commit()

        # Query summary counts
        institutions_count = session.scalar(select(func.count(Institution.id)))
        courses_count = session.scalar(select(func.count(Course.id)))
        intake_count = session.scalar(select(func.count(CourseIntake.id)))
        registry_count = session.scalar(select(func.count(MockApaarRegistry.id)))
        students_2025 = session.scalar(
            select(func.count(Student.id)).where(Student.academic_year == "2025-26")
        )
        students_2026 = session.scalar(
            select(func.count(Student.id)).where(Student.academic_year == "2026-27")
        )
        submissions_count = session.scalar(select(func.count(Submission.id)))
        flags_count = session.scalar(select(func.count(ValidationFlag.id)))
        users_count = session.scalar(select(func.count(User.id)))

        summary = {
            "institutions": institutions_count,
            "courses": courses_count,
            "course_intake": intake_count,
            "mock_apaar_registry": registry_count,
            "students_2025_26": students_2025,
            "students_2026_27": students_2026,
            "submissions": submissions_count,
            "validation_flags": flags_count,
            "demo_accounts": users_count,
            "demo_csvs": demo_csvs,
        }

        print("\n" + "=" * 62)
        print("                 APAAR PLATFORM SEED COMPLETE                 ")
        print("=" * 62)
        print(
            f"Institutions:           {institutions_count:>5} "
            f"(20 active, 5 pending, 5 not activated)"
        )
        print(f"Courses:                {courses_count:>5}")
        print(f"Course Intake Records:  {intake_count:>5} (2025-26 and 2026-27)")
        print(f"Mock APAAR Registry:    {registry_count:>5} simulated identities")
        print(f"2025-26 Students:       {students_2025:>5} (Accepted History)")
        print(f"2026-27 Students:       {students_2026:>5} (Mixed States)")
        print(f"Submissions:            {submissions_count:>5}")
        print(f"Validation Flags:       {flags_count:>5} (Intake, Jump, Cluster, Sequential, Dupe)")
        print(
            f"User Accounts:          {users_count:>5} "
            f"(aicte_admin, aicte_officer, 3 college_admins, verifier)"
        )
        print(
            f"Demo CSVs Generated:    {len(demo_csvs):>5} in demo/ "
            f"(clean, messy, overintake, cross_college_dupe)"
        )
        print("=" * 62 + "\n")

        return summary
    finally:
        if close_session:
            session.close()


if __name__ == "__main__":
    seed_all()
