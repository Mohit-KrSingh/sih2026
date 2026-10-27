"""SQLAlchemy 2.0 models for the APAAR Student Data Management and Verification System.

Defines all tables specified in SPEC.md section 7:
1. users
2. institutions
3. courses
4. course_intake
5. course_intake_history
6. activation_requests
7. correction_requests
8. seat_declarations
9. submissions
10. students
11. uploads
12. validation_flags
13. justifications
14. review_items
15. queries
16. change_requests
17. notifications
18. verified_records
19. verifiers
20. consent_requests
21. audit_log
22. api_keys
23. rule_config
24. anomaly_scores
25. mock_apaar_registry
26. dev_outbox
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TimestampMixin:
    """Timestamp mixin adding created_at and updated_at to all tables."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampMixin, Base):
    """User accounts across all roles (college, AICTE, verifier)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # college_admin, college_staff, college_viewer, aicte_officer, aicte_admin, verifier
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    institution: Mapped["Institution | None"] = relationship("Institution", back_populates="users")


class Institution(TimestampMixin, Base):
    """AICTE-approved educational institutions."""

    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aicte_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    official_email: Mapped[str] = mapped_column(String(255), nullable=False)
    official_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    head_name: Mapped[str] = mapped_column(String(255), nullable=False)
    affiliating_university: Mapped[str] = mapped_column(String(255), nullable=False)
    approval_status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False
    )  # active | suspended | withdrawn | expired
    approval_valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    account_status: Mapped[str] = mapped_column(
        String(50), default="not_activated", nullable=False
    )  # not_activated | pending_approval | active

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="institution")
    courses: Mapped[list["Course"]] = relationship(
        "Course", back_populates="institution", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission", back_populates="institution", cascade="all, delete-orphan"
    )
    students: Mapped[list["Student"]] = relationship(
        "Student", back_populates="institution", cascade="all, delete-orphan"
    )
    uploads: Mapped[list["Upload"]] = relationship(
        "Upload", back_populates="institution", cascade="all, delete-orphan"
    )
    activation_requests: Mapped[list["ActivationRequest"]] = relationship(
        "ActivationRequest", back_populates="institution", cascade="all, delete-orphan"
    )
    correction_requests: Mapped[list["CorrectionRequest"]] = relationship(
        "CorrectionRequest", back_populates="institution", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(
        "ApiKey", back_populates="institution", cascade="all, delete-orphan"
    )


class Course(TimestampMixin, Base):
    """Approved courses offered by an institution."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(50), nullable=False)  # UG | PG | Diploma | PGDM
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_years: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    supernumerary_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "institution_id", "name", "branch", "level", name="uq_courses_inst_name_branch_level"
        ),
    )

    # Relationships
    institution: Mapped["Institution"] = relationship("Institution", back_populates="courses")
    intakes: Mapped[list["CourseIntake"]] = relationship(
        "CourseIntake", back_populates="course", cascade="all, delete-orphan"
    )
    intake_history: Mapped[list["CourseIntakeHistory"]] = relationship(
        "CourseIntakeHistory", back_populates="course", cascade="all, delete-orphan"
    )
    seat_declarations: Mapped[list["SeatDeclaration"]] = relationship(
        "SeatDeclaration", back_populates="course", cascade="all, delete-orphan"
    )
    students: Mapped[list["Student"]] = relationship(
        "Student", back_populates="course", cascade="all, delete-orphan"
    )


class CourseIntake(TimestampMixin, Base):
    """Approved intake and supernumerary quota per course per academic year."""

    __tablename__ = "course_intake"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    approved_intake: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    supernumerary_seats_allowed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="aicte_master", nullable=False)
    set_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("course_id", "academic_year", name="uq_course_intake_course_year"),
    )

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="intakes")


class CourseIntakeHistory(TimestampMixin, Base):
    """Audit history of intake adjustments made by AICTE officers."""

    __tablename__ = "course_intake_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    approved_intake: Mapped[int] = mapped_column(Integer, nullable=False)
    supernumerary_seats_allowed: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    set_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="intake_history")


class ActivationRequest(TimestampMixin, Base):
    """Institution account activation claims submitted to AICTE for approval."""

    __tablename__ = "activation_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    signatory_name: Mapped[str] = mapped_column(String(255), nullable=False)
    signatory_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    letter_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending | approved | rejected
    decided_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    institution: Mapped["Institution"] = relationship(
        "Institution", back_populates="activation_requests"
    )
    decider: Mapped["User | None"] = relationship("User")


class CorrectionRequest(TimestampMixin, Base):
    """Requests raised by institutions to correct AICTE-owned data."""

    __tablename__ = "correction_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending | approved | rejected
    resolved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    institution: Mapped["Institution"] = relationship(
        "Institution", back_populates="correction_requests"
    )
    resolver: Mapped["User | None"] = relationship("User")


class SeatDeclaration(TimestampMixin, Base):
    """Declared counts of admitted seats per course per academic year."""

    __tablename__ = "seat_declarations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    regular_admitted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    supernumerary_admitted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nri_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    oci_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fn_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False
    )  # draft | declared | locked

    __table_args__ = (
        UniqueConstraint("course_id", "academic_year", name="uq_seat_declarations_course_year"),
    )

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="seat_declarations")


class Submission(TimestampMixin, Base):
    """Annual institutional submission lifecycle."""

    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False
    )  # draft | submitted | submitted_with_exceptions | under_review | accepted | query_raised
    submitted_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    receipt_no: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    declaration_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("institution_id", "academic_year", name="uq_submissions_inst_year"),
    )

    # Relationships
    institution: Mapped["Institution"] = relationship("Institution", back_populates="submissions")
    submitter: Mapped["User | None"] = relationship("User")
    students: Mapped[list["Student"]] = relationship("Student", back_populates="submission")
    validation_flags: Mapped[list["ValidationFlag"]] = relationship(
        "ValidationFlag", back_populates="submission", cascade="all, delete-orphan"
    )
    review_items: Mapped[list["ReviewItem"]] = relationship(
        "ReviewItem", back_populates="submission", cascade="all, delete-orphan"
    )
    queries: Mapped[list["Query"]] = relationship(
        "Query", back_populates="submission", cascade="all, delete-orphan"
    )


class Student(TimestampMixin, Base):
    """Enrolled student record keyed by APAAR ID."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True
    )
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    apaar_id: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dob_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    enrolment_no: Mapped[str] = mapped_column(String(100), nullable=False)
    admission_date: Mapped[date] = mapped_column(Date, nullable=False)
    admission_mode: Mapped[str] = mapped_column(String(100), nullable=False)
    seat_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Regular | Supernumerary
    reservation_category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # General, OBC, SC, ST, EWS
    nri: Mapped[str] = mapped_column(String(10), default="No", nullable=False)  # Yes | No
    oci: Mapped[str] = mapped_column(String(10), default="No", nullable=False)  # Yes | No
    foreign_national: Mapped[str] = mapped_column(
        String(10), default="No", nullable=False
    )  # Yes | No
    fn_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False
    )  # draft, valid, flagged, submitted, verified, verified_with_exception, withdrawn
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submission_id: Mapped[int | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(
        String(20), default="form", nullable=False
    )  # form | csv | api

    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "course_id",
            "academic_year",
            "apaar_id",
            name="uq_students_inst_course_year_apaar",
        ),
        Index("ix_students_apaar_academic_year", "apaar_id", "academic_year"),
        Index("ix_students_course_year_enrolment", "course_id", "academic_year", "enrolment_no"),
    )

    # Relationships
    institution: Mapped["Institution"] = relationship("Institution", back_populates="students")
    course: Mapped["Course"] = relationship("Course", back_populates="students")
    submission: Mapped["Submission | None"] = relationship("Submission", back_populates="students")
    flags: Mapped[list["ValidationFlag"]] = relationship(
        "ValidationFlag", back_populates="student", cascade="all, delete-orphan"
    )
    change_requests: Mapped[list["ChangeRequest"]] = relationship(
        "ChangeRequest", back_populates="student", cascade="all, delete-orphan"
    )
    verified_record: Mapped["VerifiedRecord | None"] = relationship(
        "VerifiedRecord", back_populates="student", uselist=False, cascade="all, delete-orphan"
    )


class Upload(TimestampMixin, Base):
    """Batch student CSV/Excel file uploads."""

    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="processing", nullable=False
    )  # processing | completed | failed
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    institution: Mapped["Institution"] = relationship("Institution", back_populates="uploads")
    uploader: Mapped["User | None"] = relationship("User")


class ValidationFlag(TimestampMixin, Base):
    """Validation violations, anomalies, exceptions and warnings."""

    __tablename__ = "validation_flags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True
    )
    submission_id: Mapped[int | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    level: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # error | exception | warning | info
    field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    fix_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience: Mapped[str] = mapped_column(
        String(50), default="both", nullable=False
    )  # college | aicte | both
    requires_justification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="open", nullable=False
    )  # open | justified | resolved | dismissed

    __table_args__ = (Index("ix_validation_flags_submission_id_level", "submission_id", "level"),)

    # Relationships
    student: Mapped["Student | None"] = relationship("Student", back_populates="flags")
    course: Mapped["Course | None"] = relationship("Course")
    submission: Mapped["Submission | None"] = relationship(
        "Submission", back_populates="validation_flags"
    )
    justifications: Mapped[list["Justification"]] = relationship(
        "Justification", back_populates="flag", cascade="all, delete-orphan"
    )


class Justification(TimestampMixin, Base):
    """Institution written justifications and supporting document references for flagged items."""

    __tablename__ = "justifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flag_id: Mapped[int] = mapped_column(
        ForeignKey("validation_flags.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    document_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    by_user: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    flag: Mapped["ValidationFlag"] = relationship("ValidationFlag", back_populates="justifications")
    author: Mapped["User | None"] = relationship("User")


class ReviewItem(TimestampMixin, Base):
    """Items in the AICTE officer review queue."""

    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    flag_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending | under_review | accepted | query_raised | escalated
    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decision: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # accept | query | escalate
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    submission: Mapped["Submission"] = relationship("Submission", back_populates="review_items")
    assignee: Mapped["User | None"] = relationship("User")
    queries: Mapped[list["Query"]] = relationship(
        "Query", back_populates="review_item", cascade="all, delete-orphan"
    )


class Query(TimestampMixin, Base):
    """Clarification queries exchanged between AICTE officers and institutions."""

    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("review_items.id", ondelete="CASCADE"), nullable=True, index=True
    )
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending | answered | closed
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    responded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    review_item: Mapped["ReviewItem | None"] = relationship("ReviewItem", back_populates="queries")
    submission: Mapped["Submission"] = relationship("Submission", back_populates="queries")


class ChangeRequest(TimestampMixin, Base):
    """Post-lock record change requests submitted by institutions to AICTE."""

    __tablename__ = "change_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending | approved | rejected
    decided_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    document_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="change_requests")
    decider: Mapped["User | None"] = relationship("User")


class Notification(TimestampMixin, Base):
    """System notifications dispatched to institutions or users."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    institution: Mapped["Institution | None"] = relationship("Institution")
    user: Mapped["User | None"] = relationship("User")


class VerifiedRecord(TimestampMixin, Base):
    """Cryptographically signed verifiable credentials issued for student records."""

    __tablename__ = "verified_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    verification_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False
    )  # active | revoked

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="verified_record")


class Verifier(TimestampMixin, Base):
    """Registered and approved verifier organisations (employers, regulators)."""

    __tablename__ = "verifiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # employer | regulator | institution
    contact: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending | approved | revoked

    # Relationships
    consent_requests: Mapped[list["ConsentRequest"]] = relationship(
        "ConsentRequest", back_populates="verifier", cascade="all, delete-orphan"
    )


class ConsentRequest(TimestampMixin, Base):
    """Student consent requests initiated by verifiers."""

    __tablename__ = "consent_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verifier_id: Mapped[int] = mapped_column(
        ForeignKey("verifiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    apaar_id: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending | approved | denied | expired
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    verifier: Mapped["Verifier"] = relationship("Verifier", back_populates="consent_requests")


class AuditLog(TimestampMixin, Base):
    """Tamper-evident append-only hash-chained audit log."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    actor_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    before_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)


class ApiKey(TimestampMixin, Base):
    """Scoped institutional integration API keys."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    scopes: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    institution: Mapped["Institution"] = relationship("Institution", back_populates="api_keys")


class RuleConfig(TimestampMixin, Base):
    """Validation rule configurations and policy overrides."""

    __tablename__ = "rule_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    level: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # error | exception | warning | info
    params_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    updater: Mapped["User | None"] = relationship("User")


class AnomalyScore(TimestampMixin, Base):
    """ML and statistical anomaly detection scores per course per year."""

    __tablename__ = "anomaly_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    features_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "course_id",
            "academic_year",
            name="uq_anomaly_scores_inst_course_year",
        ),
    )

    # Relationships
    institution: Mapped["Institution"] = relationship("Institution")
    course: Mapped["Course"] = relationship("Course")


class MockApaarRegistry(TimestampMixin, Base):
    """Mock simulated external APAAR ID identity registry."""

    __tablename__ = "mock_apaar_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    apaar_id: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)


class DevOutbox(TimestampMixin, Base):
    """Local simulation outbox for OTPs, emails, and SMS notifications."""

    __tablename__ = "dev_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # email | sms | otp | notification
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
