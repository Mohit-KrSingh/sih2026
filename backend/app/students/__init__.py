"""Student data models, services, and operations."""

from app.students.duplicate_service import (
    notify_duplicate_enrolment,
    query_duplicates_by_apaar_and_year,
    resolve_duplicate_flags_on_status_change,
)
from app.students.seat_declarations import (
    batch_save_seat_declarations,
    get_course_summary,
    get_institution_seat_declarations,
    save_course_seat_declaration,
)
from app.students.service import (
    create_student,
    delete_student,
    get_student,
    list_students,
    update_student,
)

__all__ = [
    "notify_duplicate_enrolment",
    "query_duplicates_by_apaar_and_year",
    "resolve_duplicate_flags_on_status_change",
    "get_institution_seat_declarations",
    "get_course_summary",
    "save_course_seat_declaration",
    "batch_save_seat_declarations",
    "create_student",
    "delete_student",
    "get_student",
    "list_students",
    "update_student",
]
