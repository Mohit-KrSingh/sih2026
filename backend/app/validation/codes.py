"""Standard rule codes and metadata catalogue per SPEC.md Section 9.3."""

from typing import Any

from app.validation.flags import ValidationLevel, ValidationScope

# File Scope Rules
FILE_TEMPLATE = "FILE_TEMPLATE"
FILE_EMPTY = "FILE_EMPTY"
FILE_TOO_LARGE = "FILE_TOO_LARGE"
DUP_APAAR_IN_FILE = "DUP_APAAR_IN_FILE"
DUP_ENROLNO_IN_COURSE = "DUP_ENROLNO_IN_COURSE"

# Row Scope Rules
APAAR_REQUIRED = "APAAR_REQUIRED"
APAAR_FORMAT = "APAAR_FORMAT"
NAME_REQUIRED = "NAME_REQUIRED"
NAME_FORMAT = "NAME_FORMAT"
DOB_INVALID = "DOB_INVALID"
ENUM_INVALID = "ENUM_INVALID"
COUNTRY_REQUIRED = "COUNTRY_REQUIRED"
ADMISSION_DATE_WINDOW = "ADMISSION_DATE_WINDOW"
APAAR_NOT_FOUND = "APAAR_NOT_FOUND"
APAAR_NAME_MISMATCH = "APAAR_NAME_MISMATCH"
APAAR_DOB_MISMATCH = "APAAR_DOB_MISMATCH"
CATEGORY_CONFLICT = "CATEGORY_CONFLICT"
COURSE_NOT_APPROVED = "COURSE_NOT_APPROVED"
AGE_OUT_OF_RANGE = "AGE_OUT_OF_RANGE"
SEAT_TYPE_NOT_APPROVED = "SEAT_TYPE_NOT_APPROVED"
MODE_CATEGORY_MISMATCH = "MODE_CATEGORY_MISMATCH"
ADMISSION_YEAR_MISMATCH = "ADMISSION_YEAR_MISMATCH"

# Course Scope Rules
INTAKE_EXCEEDED = "INTAKE_EXCEEDED"
SUPERNUMERARY_EXCEEDED = "SUPERNUMERARY_EXCEEDED"
SEAT_DECLARATION_MISMATCH = "SEAT_DECLARATION_MISMATCH"

# Cross-College Scope Rules
DUP_ACTIVE_OTHER_COLLEGE = "DUP_ACTIVE_OTHER_COLLEGE"
DUP_SAME_COURSE_OTHER_COLLEGE = "DUP_SAME_COURSE_OTHER_COLLEGE"

# Anomaly Scope Rules
ANOM_ENROLMENT_JUMP = "ANOM_ENROLMENT_JUMP"
ANOM_NRI_SHARE = "ANOM_NRI_SHARE"
ANOM_SUPERNUM_SHARE = "ANOM_SUPERNUM_SHARE"
ANOM_DOB_CLUSTER = "ANOM_DOB_CLUSTER"
ANOM_SEQUENTIAL_APAAR = "ANOM_SEQUENTIAL_APAAR"
ANOM_SAME_ADMISSION_DAY = "ANOM_SAME_ADMISSION_DAY"
ANOM_MODEL_SCORE = "ANOM_MODEL_SCORE"


# Complete metadata contract per SPEC.md Section 9.3
RULE_CATALOGUE: dict[str, dict[str, Any]] = {
    FILE_TEMPLATE: {
        "scope": ValidationScope.FILE,
        "default_level": ValidationLevel.ERROR,
        "meaning": "Wrong or missing columns. File rejected, nothing saved",
    },
    FILE_EMPTY: {
        "scope": ValidationScope.FILE,
        "default_level": ValidationLevel.ERROR,
        "meaning": "No data rows. File rejected",
    },
    FILE_TOO_LARGE: {
        "scope": ValidationScope.FILE,
        "default_level": ValidationLevel.ERROR,
        "meaning": "Over the row limit (default 10,000). File rejected",
        "default_params": {"max_rows": 10000},
    },
    APAAR_REQUIRED: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.ERROR,
        "meaning": "APAAR ID missing",
    },
    APAAR_FORMAT: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.ERROR,
        "meaning": "Not exactly 12 digits",
    },
    NAME_REQUIRED: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.ERROR,
        "meaning": "Name missing",
    },
    NAME_FORMAT: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.ERROR,
        "meaning": "Name has digits or illegal characters",
    },
    DOB_INVALID: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.ERROR,
        "meaning": "Not a valid date, or in the future",
    },
    ENUM_INVALID: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.ERROR,
        "meaning": "Value not in the allowed list (gender, category, seat type, mode, Yes/No)",
    },
    COUNTRY_REQUIRED: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.ERROR,
        "meaning": "Foreign national is Yes but country is empty",
    },
    ADMISSION_DATE_WINDOW: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.WARNING,
        "meaning": "Admission date outside the admission window for that year",
    },
    APAAR_NOT_FOUND: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.ERROR,
        "meaning": "ID does not exist in the registry",
    },
    APAAR_NAME_MISMATCH: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.WARNING,
        "meaning": "Fuzzy name match below threshold (default 85)",
        "default_params": {"threshold": 85},
    },
    APAAR_DOB_MISMATCH: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.ERROR,
        "meaning": "Date of birth differs from the registry",
    },
    CATEGORY_CONFLICT: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.ERROR,
        "meaning": "NRI and foreign national both Yes",
    },
    COURSE_NOT_APPROVED: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.ERROR,
        "meaning": "Course or branch not approved for this college",
    },
    AGE_OUT_OF_RANGE: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.WARNING,
        "meaning": (
            "Age outside the course-level band (defaults: UG 15-30, PG 19-45, "
            "Diploma 14-30, PGDM 19-45)"
        ),
        "default_params": {
            "bands": {
                "UG": (15, 30),
                "PG": (19, 45),
                "Diploma": (14, 30),
                "PGDM": (19, 45),
            }
        },
    },
    SEAT_TYPE_NOT_APPROVED: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.ERROR,
        "meaning": "Supernumerary seat in a course with no supernumerary seats allowed",
    },
    MODE_CATEGORY_MISMATCH: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.WARNING,
        "meaning": (
            "NRI/OCI/foreign student not admitted through the NRI/OCI/foreign quota, or the reverse"
        ),
    },
    ADMISSION_YEAR_MISMATCH: {
        "scope": ValidationScope.ROW,
        "default_level": ValidationLevel.WARNING,
        "meaning": "Admission date does not fall in the stated academic year",
    },
    DUP_APAAR_IN_FILE: {
        "scope": ValidationScope.FILE,
        "default_level": ValidationLevel.ERROR,
        "meaning": (
            "Same APAAR ID appears twice in the upload or the college's records for that year"
        ),
    },
    DUP_ENROLNO_IN_COURSE: {
        "scope": ValidationScope.FILE,
        "default_level": ValidationLevel.ERROR,
        "meaning": "Same enrolment number twice in one course and year",
    },
    DUP_ACTIVE_OTHER_COLLEGE: {
        "scope": ValidationScope.CROSS,
        "default_level": ValidationLevel.WARNING,
        "meaning": (
            "APAAR ID is active at another AICTE college this academic year. "
            "Both colleges notified. Resolved when one marks student withdrawn or transferred"
        ),
    },
    DUP_SAME_COURSE_OTHER_COLLEGE: {
        "scope": ValidationScope.CROSS,
        "default_level": ValidationLevel.EXCEPTION,
        "meaning": "Same APAAR ID in the same course and year at another college",
    },
    INTAKE_EXCEEDED: {
        "scope": ValidationScope.COURSE,
        "default_level": ValidationLevel.EXCEPTION,
        "meaning": (
            "Regular admitted is above approved intake. Message states the exact overshoot"
        ),
    },
    SUPERNUMERARY_EXCEEDED: {
        "scope": ValidationScope.COURSE,
        "default_level": ValidationLevel.EXCEPTION,
        "meaning": "Supernumerary admitted is above the supernumerary seats AICTE allows",
    },
    SEAT_DECLARATION_MISMATCH: {
        "scope": ValidationScope.COURSE,
        "default_level": ValidationLevel.ERROR,
        "meaning": (
            "Declared counts differ from uploaded student list. Blocks submit; college fixes either"
        ),
    },
    ANOM_ENROLMENT_JUMP: {
        "scope": ValidationScope.ANOMALY,
        "default_level": ValidationLevel.WARNING,
        "meaning": (
            "Enrolment up more than a threshold (default 30%) against last year. Audience: aicte"
        ),
        "default_params": {"threshold_percent": 30.0},
    },
    ANOM_NRI_SHARE: {
        "scope": ValidationScope.ANOMALY,
        "default_level": ValidationLevel.WARNING,
        "meaning": "NRI/OCI/foreign share unusually high (default over 25%). Audience: aicte",
        "default_params": {"threshold_percent": 25.0},
    },
    ANOM_SUPERNUM_SHARE: {
        "scope": ValidationScope.ANOMALY,
        "default_level": ValidationLevel.WARNING,
        "meaning": "Supernumerary share unusually high (default over 15%). Audience: aicte",
        "default_params": {"threshold_percent": 15.0},
    },
    ANOM_DOB_CLUSTER: {
        "scope": ValidationScope.ANOMALY,
        "default_level": ValidationLevel.WARNING,
        "meaning": "Many students share one date of birth (default 5 or more). Audience: aicte",
        "default_params": {"threshold_count": 5},
    },
    ANOM_SEQUENTIAL_APAAR: {
        "scope": ValidationScope.ANOMALY,
        "default_level": ValidationLevel.WARNING,
        "meaning": "Long runs of sequential APAAR IDs (default 10 or more). Audience: aicte",
        "default_params": {"threshold_run": 10},
    },
    ANOM_SAME_ADMISSION_DAY: {
        "scope": ValidationScope.ANOMALY,
        "default_level": ValidationLevel.INFO,
        "meaning": (
            "Large share of students admitted on one day (default over 60%). Audience: aicte"
        ),
        "default_params": {"threshold_percent": 60.0},
    },
    ANOM_MODEL_SCORE: {
        "scope": ValidationScope.ANOMALY,
        "default_level": ValidationLevel.WARNING,
        "meaning": (
            "IsolationForest score on college-course features flags this as unusual. "
            "Audience: aicte"
        ),
    },
}
