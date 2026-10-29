export type ReportFormat = "csv" | "xlsx" | "pdf";

export type ReportType =
  | "enrolment-by-state-course"
  | "seat-utilisation"
  | "colleges-with-exceptions"
  | "duplicate-enrolments"
  | "year-over-year-trends"
  | "accreditation-snapshot"
  | "college-submission";

export interface ReportSummaryBox {
  label: string;
  value: string | number;
  detail?: string;
}

export interface ReportPreviewResponse {
  report_type: string;
  title: string;
  subtitle: string;
  academic_year: string;
  generated_at: string;
  filters_applied: Record<string, unknown>;
  summary_boxes: ReportSummaryBox[];
  columns: string[];
  rows: (string | number)[][];
  totals_row?: (string | number)[];
  total_records: number;
  notes: string[];
}

export interface ReportFilterState {
  academic_year: string;
  state?: string;
  course?: string;
  institution_id?: number;
  course_id?: number;
  base_year?: string;
  target_year?: string;
}
