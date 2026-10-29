"""Pydantic schemas and dataclasses for reports generation."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ReportFormat(StrEnum):
    """Supported output formats for reports."""

    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


class ReportType(StrEnum):
    """The seven official reports mandated by SPEC.md Section 17."""

    ENROLMENT_BY_STATE_COURSE = "enrolment-by-state-course"
    SEAT_UTILISATION = "seat-utilisation"
    COLLEGES_WITH_EXCEPTIONS = "colleges-with-exceptions"
    DUPLICATE_ENROLMENTS = "duplicate-enrolments"
    YEAR_OVER_YEAR_TRENDS = "year-over-year-trends"
    ACCREDITATION_SNAPSHOT = "accreditation-snapshot"
    COLLEGE_SUBMISSION = "college-submission"


class ReportSummaryBox(BaseModel):
    """High-level key-value metric box shown on report headers / UI."""

    label: str
    value: str | int | float
    detail: str | None = None


class ReportData(BaseModel):
    """Unified report representation for exporting to CSV, XLSX, and PDF."""

    report_type: ReportType
    title: str
    subtitle: str
    academic_year: str
    generated_at: str
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    summary_boxes: list[ReportSummaryBox] = Field(default_factory=list)
    columns: list[str]
    rows: list[list[Any]]
    totals_row: list[Any] | None = None
    notes: list[str] = Field(default_factory=list)


class ReportPreviewResponse(BaseModel):
    """Preview JSON response for rendering in frontend data tables before export."""

    report_type: str
    title: str
    subtitle: str
    academic_year: str
    generated_at: str
    filters_applied: dict[str, Any]
    summary_boxes: list[ReportSummaryBox]
    columns: list[str]
    rows: list[list[Any]]
    totals_row: list[Any] | None = None
    total_records: int
    notes: list[str] = Field(default_factory=list)


class ReportFilterParams(BaseModel):
    """Standardized report filter query parameters."""

    academic_year: str = "2026-27"
    state: str | None = None
    course: str | None = None
    institution_id: int | None = None
    course_id: int | None = None
    format: ReportFormat = ReportFormat.CSV
