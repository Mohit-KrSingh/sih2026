"""Student bulk upload processing, parsing, draft persistence, and validation."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime
from typing import Any

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import service as audit_service
from app.auth.security import encrypt_dob
from app.institutions.service import check_institution_can_upload
from app.models import Course, Institution, Student, Upload, User
from app.students.schemas import (
    StudentValidationFlag,
    UploadHistoryItem,
    UploadHistoryResponse,
    UploadResultResponse,
    UploadRowResult,
    UploadSummary,
)
from app.validation.codes import (
    FILE_EMPTY,
    FILE_TEMPLATE,
    FILE_TOO_LARGE,
)
from app.validation.flags import ValidationLevel

EXPECTED_COLUMNS: list[str] = [
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


def _parse_iso_date(date_str: str | None, default_date: date | None = None) -> date:
    """Safely parse an ISO date string (YYYY-MM-DD), with fallback."""
    if not date_str:
        return default_date or date.today()
    try:
        return date.fromisoformat(str(date_str).strip())
    except Exception:
        return default_date or date.today()


def generate_template_csv() -> str:
    """Generate canonical CSV template content with exact lowercase headers.

    Spec 8.2: CSV columns, exactly in this order, lowercase header:
    apaar_id, name, dob, gender, course, branch, admission_year, enrolment_no,
    admission_date, admission_mode, seat_type, reservation_category, nri, oci,
    foreign_national, country
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(EXPECTED_COLUMNS)

    # Include two sample compliant rows for user reference
    sample_rows = [
        [
            "900012345678",
            "Rahul Sharma",
            "2004-05-15",
            "Male",
            "Computer Science and Engineering",
            "Computer Science",
            "2026-27",
            "ENR-2026-001",
            "2026-07-15",
            "State counselling",
            "Regular",
            "General",
            "No",
            "No",
            "No",
            "",
        ],
        [
            "900087654321",
            "Priya Patel",
            "2003-11-20",
            "Female",
            "Computer Science and Engineering",
            "Computer Science",
            "2026-27",
            "ENR-2026-002",
            "2026-07-20",
            "State counselling",
            "Regular",
            "OBC",
            "No",
            "No",
            "No",
            "",
        ],
    ]
    for r in sample_rows:
        writer.writerow(r)

    return output.getvalue()


def parse_uploaded_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Parse uploaded file bytes with pandas and enforce file-level validation rules.

    Rejection policy: Only unreadable, empty, oversized, or malformed-header files are rejected.
    """
    fname_lower = filename.lower()
    df: pd.DataFrame | None = None

    try:
        if fname_lower.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        else:
            # Attempt parsing text/csv with encoding fallbacks
            for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
                try:
                    text_content = file_bytes.decode(enc)
                    sep = "\t" if fname_lower.endswith(".tsv") else ","
                    df = pd.read_csv(io.StringIO(text_content), sep=sep, dtype=str)
                    break
                except UnicodeDecodeError:
                    continue
                except Exception:
                    break
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unreadable file: Unable to parse file format ({exc}).",
        ) from exc

    if df is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unreadable file: Unable to decode file with supported text "
                "or spreadsheet encodings."
            ),
        )

    # Normalize NaN values to empty string
    df = df.fillna("")

    # Strip column names and convert to lowercase
    normalized_cols = [str(c).strip().lower() for c in df.columns]
    df.columns = normalized_cols

    # FILE_TEMPLATE check: Ensure all required columns exist
    missing_cols = [c for c in EXPECTED_COLUMNS if c not in normalized_cols]
    if missing_cols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File rejected ({FILE_TEMPLATE}): Missing required column(s): "
                f"{', '.join(missing_cols)}. Download template for format."
            ),
        )

    # FILE_EMPTY check: Ensure at least one data row
    if len(df) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File rejected ({FILE_EMPTY}): Uploaded file contains no student data rows.",
        )

    # FILE_TOO_LARGE check: Ensure not exceeding row limit
    if len(df) > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File rejected ({FILE_TOO_LARGE}): Uploaded file contains {len(df):,} rows, "
                "which exceeds the maximum limit of 10,000 rows."
            ),
        )

    return df


def _process_parsed_records(
    db: Session,
    institution_id: int,
    raw_records: list[dict[str, Any]],
    filename: str,
    source: str = "csv",
    actor_id: int | None = None,
    actor_role: str = "college_staff",
    academic_year_default: str = "2026-27",
    client_ip: str | None = None,
) -> UploadResultResponse:
    """Core evaluation engine processing parsed records (CSV or JSON API).

    Spec 8.2, 9.4, 13, 17 & Hard Rule 4:
    - Re-upload updates matching records (same college, course, year, APAAR ID).
    - Runs unified validation engine across all rows and persists flags.
    - Saves Upload history record and writes hash-chained audit log.
    """
    # 3. Fetch institution's approved courses
    approved_courses = list(
        db.scalars(
            select(Course).where(Course.institution_id == institution_id)
        ).all()
    )

    # Course lookup helpers
    def match_course(c_name: str, c_branch: str, c_id: int | None = None) -> Course | None:
        if c_id is not None:
            for ac in approved_courses:
                if ac.id == c_id:
                    return ac
        norm_name = c_name.strip().lower() if c_name else ""
        norm_branch = c_branch.strip().lower() if c_branch else ""
        for ac in approved_courses:
            ac_name = ac.name.strip().lower()
            ac_branch = ac.branch.strip().lower() if ac.branch else ""
            if ac_name == norm_name:
                if not norm_branch or not ac_branch or ac_branch == norm_branch:
                    return ac
        return None

    # 4. Fetch existing institution students to support matching updates
    existing_students = list(
        db.scalars(
            select(Student).where(Student.institution_id == institution_id)
        ).all()
    )

    # Index existing by (course_id, academic_year, apaar_id) and (apaar_id, academic_year)
    existing_map: dict[tuple[int | None, str, str], Student] = {}
    for st in existing_students:
        existing_map[(st.course_id, st.academic_year, st.apaar_id)] = st

    # Track student ORM models created or updated in this upload
    student_records: list[Student] = []
    student_mapping: dict[int, Student] = {}  # row_number -> Student
    normalized_row_dicts: list[dict[str, Any]] = []

    inserted_count = 0
    updated_count = 0
    batch_seen_keys: set[tuple[int | None, str, str]] = set()

    def _to_bool_str(val: Any) -> str:
        if isinstance(val, bool):
            return "Yes" if val else "No"
        s = str(val).strip().lower()
        return "Yes" if s in {"yes", "true", "1", "y"} else "No"

    for idx, raw in enumerate(raw_records, start=1):
        apaar_raw = str(raw.get("apaar_id", "")).strip()
        name_raw = str(raw.get("name", "")).strip()
        dob_raw = str(raw.get("dob", "")).strip()
        gender_raw = str(raw.get("gender", "")).strip()
        course_raw = str(raw.get("course", "")).strip()
        branch_raw = str(raw.get("branch", "")).strip()

        c_id_raw = raw.get("course_id")
        try:
            c_str = str(c_id_raw).strip() if c_id_raw is not None else ""
            course_id_hint = int(c_str) if c_str else None
        except (ValueError, TypeError):
            course_id_hint = None

        year_raw = str(raw.get("admission_year", "")).strip() or academic_year_default
        enrol_raw = str(raw.get("enrolment_no", "")).strip()
        adm_date_raw = str(raw.get("admission_date", "")).strip()
        mode_raw = str(raw.get("admission_mode", "")).strip()
        seat_raw = str(raw.get("seat_type", "")).strip()
        cat_raw = str(raw.get("reservation_category", "")).strip()
        nri_raw = _to_bool_str(raw.get("nri", "No"))
        oci_raw = _to_bool_str(raw.get("oci", "No"))
        fn_raw = _to_bool_str(raw.get("foreign_national", "No"))
        country_raw = str(raw.get("country", "")).strip()

        # Match course
        matched = match_course(course_raw, branch_raw, course_id_hint)
        course_id = matched.id if matched else None

        # Foreign national country check
        is_foreign = fn_raw.lower() == "yes"
        fn_country = country_raw if (is_foreign and country_raw) else None

        parsed_adm_date = _parse_iso_date(adm_date_raw)
        encrypted_dob = encrypt_dob(dob_raw if dob_raw else "2000-01-01")

        # Handle APAAR key for database uniqueness
        # If apaar_id is missing or already seen in this exact batch, use a scoped draft key
        is_clean_apaar = len(apaar_raw) == 12 and apaar_raw.isdigit()
        batch_key = (course_id, year_raw, apaar_raw)
        is_intra_batch_dupe = batch_key in batch_seen_keys

        if not apaar_raw:
            db_apaar = f"DFT{idx:09d}"
        elif is_intra_batch_dupe:
            db_apaar = f"DUP{idx:05d}{apaar_raw[:4]}"
        else:
            db_apaar = apaar_raw

        batch_seen_keys.add(batch_key)

        # Re-upload matching records: check if (course_id, academic_year, apaar_id) exists
        existing_student: Student | None = None
        if is_clean_apaar and not is_intra_batch_dupe:
            existing_student = existing_map.get((course_id, year_raw, apaar_raw))

        if existing_student is not None and not existing_student.is_locked:
            # Update matching record
            existing_student.name = name_raw
            existing_student.dob_encrypted = encrypted_dob
            existing_student.gender = gender_raw
            existing_student.enrolment_no = enrol_raw
            existing_student.admission_date = parsed_adm_date
            existing_student.admission_mode = mode_raw
            existing_student.seat_type = seat_raw
            existing_student.reservation_category = cat_raw
            existing_student.nri = nri_raw
            existing_student.oci = oci_raw
            existing_student.foreign_national = fn_raw
            existing_student.fn_country = fn_country
            existing_student.source = source
            existing_student.status = "draft"
            if matched:
                existing_student.course = matched
            student_obj = existing_student
            updated_count += 1
        else:
            # Create new draft student
            student_obj = Student(
                institution_id=institution_id,
                course_id=course_id,
                academic_year=year_raw,
                apaar_id=db_apaar,
                name=name_raw,
                dob_encrypted=encrypted_dob,
                gender=gender_raw,
                enrolment_no=enrol_raw,
                admission_date=parsed_adm_date,
                admission_mode=mode_raw,
                seat_type=seat_raw,
                reservation_category=cat_raw,
                nri=nri_raw,
                oci=oci_raw,
                foreign_national=fn_raw,
                fn_country=fn_country,
                status="draft",
                is_locked=False,
                source=source,
            )
            if matched:
                student_obj.course = matched
            db.add(student_obj)
            inserted_count += 1

        student_records.append(student_obj)
        student_mapping[idx] = student_obj

        # Build normalized dictionary representing the raw row for validation engine
        row_dict = {
            "row_number": idx,
            "apaar_id": apaar_raw,  # Use raw entered APAAR ID so format/required rules fire
            "name": name_raw,
            "dob": dob_raw,
            "gender": gender_raw,
            "course": course_raw,
            "branch": branch_raw,
            "course_id": course_id,
            "admission_year": year_raw,
            "enrolment_no": enrol_raw,
            "admission_date": adm_date_raw,
            "admission_mode": mode_raw,
            "seat_type": seat_raw,
            "reservation_category": cat_raw,
            "nri": nri_raw,
            "oci": oci_raw,
            "foreign_national": fn_raw,
            "country": fn_country or "",
            "institution_id": institution_id,
        }
        normalized_row_dicts.append(row_dict)

    # Flush so all new students receive persistent surrogate IDs
    db.flush()

    # Link student IDs back to normalized rows
    for idx, row_dict in enumerate(normalized_row_dicts, start=1):
        st = student_mapping[idx]
        row_dict["id"] = st.id
        row_dict["student_id"] = st.id
        student_mapping[st.id] = st

    # 5. Run pure validation engine across all rows and persist flags
    from app.validation.service import validate_rows

    val_result = validate_rows(
        rows=normalized_row_dicts,
        institution_id=institution_id,
        academic_year=academic_year_default,
        db_session=db,
        persist=True,
        keep_justifications=True,
    )

    # Group flags by row_number
    flags_by_row: dict[int, list[StudentValidationFlag]] = {}
    total_errors = 0
    total_exceptions = 0
    total_warnings = 0
    total_infos = 0
    error_list_for_csv: list[dict[str, Any]] = []

    for fl in val_result:
        lvl = fl.level.value if isinstance(fl.level, ValidationLevel) else str(fl.level)
        if lvl == "error":
            total_errors += 1
        elif lvl == "exception":
            total_exceptions += 1
        elif lvl == "warning":
            total_warnings += 1
        elif lvl == "info":
            total_infos += 1

        row_num = fl.row_ref if isinstance(fl.row_ref, int) else None
        if row_num is not None and row_num in student_mapping:
            st = student_mapping[row_num]
            fl_dto = StudentValidationFlag(
                rule_code=fl.rule_code,
                level=lvl,  # type: ignore[arg-type]
                field=fl.field,
                message=fl.message,
                fix_hint=fl.fix_hint,
                audience=fl.audience.value if hasattr(fl.audience, "value") else str(fl.audience),
                requires_justification=fl.requires_justification,
                status="open",
            )
            flags_by_row.setdefault(row_num, []).append(fl_dto)

            # Record for error file export
            raw_r = normalized_row_dicts[row_num - 1]
            error_list_for_csv.append(
                {
                    "row_number": row_num,
                    "field": fl.field or "",
                    "rule_code": fl.rule_code,
                    "level": lvl,
                    "message": fl.message,
                    "fix_hint": fl.fix_hint or "",
                    "apaar_id": raw_r.get("apaar_id", ""),
                    "name": raw_r.get("name", ""),
                }
            )

    # 6. Update student status (valid vs flagged) and assemble row results
    row_results: list[UploadRowResult] = []
    valid_rows_count = 0
    flagged_rows_count = 0

    for idx, raw in enumerate(normalized_row_dicts, start=1):
        st = student_mapping[idx]
        row_flags = flags_by_row.get(idx, [])
        has_blocking = any(
            f.level in ("error", "exception", "warning") for f in row_flags
        )

        if has_blocking:
            st.status = "flagged"
            flagged_rows_count += 1
        else:
            st.status = "valid"
            valid_rows_count += 1

        row_results.append(
            UploadRowResult(
                row_number=idx,
                student_id=st.id,
                apaar_id=raw["apaar_id"],
                name=raw["name"],
                dob=raw["dob"],
                gender=raw["gender"],
                course=raw["course"],
                branch=raw["branch"],
                admission_year=raw["admission_year"],
                enrolment_no=raw["enrolment_no"],
                admission_date=raw["admission_date"],
                admission_mode=raw["admission_mode"],
                seat_type=raw["seat_type"],
                reservation_category=raw["reservation_category"],
                nri=raw["nri"],
                oci=raw["oci"],
                foreign_national=raw["foreign_national"],
                country=raw["country"] or None,
                status=st.status,
                flags=row_flags,
            )
        )

    summary = UploadSummary(
        total_rows=len(raw_records),
        valid_rows=valid_rows_count,
        flagged_rows=flagged_rows_count,
        error_count=total_errors,
        exception_count=total_exceptions,
        warning_count=total_warnings,
        info_count=total_infos,
        inserted_count=inserted_count,
        updated_count=updated_count,
    )

    # 7. Create Upload history record
    summary_dict = summary.model_dump()
    summary_payload = {
        "summary": summary_dict,
        "errors": error_list_for_csv,
        "rows": [r.model_dump() for r in row_results],
        "student_ids": [s.id for s in student_records],
    }

    upload_record = Upload(
        institution_id=institution_id,
        filename=filename,
        row_count=len(raw_records),
        status="completed",
        summary_json=summary_payload,
        uploaded_by=actor_id if source == "csv" else None,
    )
    db.add(upload_record)
    db.flush()

    # 8. Record state change in hash-chained audit log
    action_name = "student.api_push" if source == "api" else "student.bulk_upload"
    audit_service.record(
        db=db,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action_name,
        entity="upload",
        entity_id=upload_record.id,
        before_json=None,
        after_json={
            "upload_id": upload_record.id,
            "filename": filename,
            "row_count": len(raw_records),
            "summary": summary_dict,
            "source": source,
        },
        ip=client_ip,
    )

    db.commit()

    return UploadResultResponse(
        upload_id=upload_record.id,
        filename=filename,
        row_count=len(raw_records),
        summary=summary,
        rows=row_results,
    )


def process_bulk_upload(
    db: Session,
    institution_id: int,
    file_bytes: bytes,
    filename: str,
    user: User,
    academic_year_default: str = "2026-27",
    client_ip: str | None = None,
) -> UploadResultResponse:
    """Process a bulk student file upload (CSV / Excel).

    Spec 8.2, 9.4, 13:
    1. Verify institution approval status (active only).
    2. Parse with pandas; reject only unreadable files.
    3. Save/update all rows as drafts; re-upload updates matching records.
    4. Run validation engine across all rows; persist flags.
    5. Save Upload history record and write hash-chained audit log.
    6. Return summary counts, per-row badges, and flags.
    """
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution #{institution_id} not found",
        )
    check_institution_can_upload(institution)

    df = parse_uploaded_file(file_bytes, filename)
    raw_records = df.to_dict(orient="records")

    return _process_parsed_records(
        db=db,
        institution_id=institution_id,
        raw_records=raw_records,
        filename=filename,
        source="csv",
        actor_id=user.id,
        actor_role=user.role,
        academic_year_default=academic_year_default,
        client_ip=client_ip,
    )


def process_json_bulk_upload(
    db: Session,
    institution_id: int,
    records: list[dict[str, Any]],
    academic_year_default: str = "2026-27",
    api_key_name: str = "ERP Integration",
    api_key_id: int | None = None,
    client_ip: str | None = None,
) -> UploadResultResponse:
    """Process bulk student records pushed via JSON Integration API.

    Spec 8.2, 9.4, 17 & TASKS.md T36:
    1. Verify institution approval status (active only).
    2. Validate batch size (1 to 10,000 rows).
    3. Save/update all records as drafts (source="api").
    4. Run unified validation engine across all rows and persist flags.
    5. Save Upload history record and write hash-chained audit log.
    6. Return UploadResultResponse.
    """
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution #{institution_id} not found",
        )
    check_institution_can_upload(institution)

    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload contains no student records. At least 1 record is required.",
        )

    if len(records) > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch contains {len(records):,} records, exceeding the 10,000 maximum limit.",
        )

    ts_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"erp_batch_{academic_year_default}_{ts_str}.json"

    return _process_parsed_records(
        db=db,
        institution_id=institution_id,
        raw_records=records,
        filename=filename,
        source="api",
        actor_id=api_key_id,
        actor_role="api_key",
        academic_year_default=academic_year_default,
        client_ip=client_ip,
    )


def get_upload_history(
    db: Session,
    institution_id: int,
    limit: int = 20,
    offset: int = 0,
) -> UploadHistoryResponse:
    """Retrieve historical bulk uploads for an institution."""
    base_query = (
        select(Upload)
        .where(Upload.institution_id == institution_id)
        .order_by(Upload.created_at.desc(), Upload.id.desc())
    )

    total = db.scalar(
        select(func.count()).select_from(
            select(Upload.id).where(Upload.institution_id == institution_id).subquery()
        )
    ) or 0

    records = db.scalars(base_query.offset(offset).limit(limit)).all()
    items = [
        UploadHistoryItem(
            id=r.id,
            institution_id=r.institution_id,
            filename=r.filename,
            row_count=r.row_count,
            status=r.status,
            summary_json=r.summary_json,
            uploaded_by=r.uploaded_by,
            created_at=r.created_at,
        )
        for r in records
    ]

    return UploadHistoryResponse(items=items, total=total)


def get_upload_details(
    db: Session,
    institution_id: int,
    upload_id: int,
) -> UploadResultResponse:
    """Retrieve details and row evaluation results for a past upload."""
    upload = db.scalar(
        select(Upload).where(
            Upload.id == upload_id,
            Upload.institution_id == institution_id,
        )
    )
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload #{upload_id} not found",
        )

    summary_json = upload.summary_json or {}
    raw_summary = summary_json.get("summary", {})
    summary = UploadSummary(**raw_summary)

    raw_rows = summary_json.get("rows", [])
    rows = [UploadRowResult(**r) for r in raw_rows]

    return UploadResultResponse(
        upload_id=upload.id,
        filename=upload.filename,
        row_count=upload.row_count,
        summary=summary,
        rows=rows,
    )


def generate_error_csv(
    db: Session,
    institution_id: int,
    upload_id: int,
) -> str:
    """Generate CSV file containing all validation errors and fix hints for an upload.

    Spec 13 & TASKS.md T21: download error file (row, field, code, level, message, fix hint).
    """
    upload = db.scalar(
        select(Upload).where(
            Upload.id == upload_id,
            Upload.institution_id == institution_id,
        )
    )
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload #{upload_id} not found",
        )

    summary_json = upload.summary_json or {}
    errors = summary_json.get("errors", [])

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "row_number",
            "field",
            "rule_code",
            "level",
            "message",
            "fix_hint",
            "apaar_id",
            "name",
        ]
    )

    for err in errors:
        writer.writerow(
            [
                err.get("row_number", ""),
                err.get("field", ""),
                err.get("rule_code", ""),
                err.get("level", ""),
                err.get("message", ""),
                err.get("fix_hint", ""),
                err.get("apaar_id", ""),
                err.get("name", ""),
            ]
        )

    return output.getvalue()
