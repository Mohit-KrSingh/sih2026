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
from app.students.upload_service import (
    generate_error_csv,
    generate_template_csv,
    get_upload_details,
    get_upload_history,
    parse_uploaded_file,
    process_bulk_upload,
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
    "generate_template_csv",
    "parse_uploaded_file",
    "process_bulk_upload",
    "get_upload_history",
    "get_upload_details",
    "generate_error_csv",
]
