/**
 * TypeScript types for annual submission lifecycle, submit gate, and receipts.
 * SPEC.md Section 10 & TASKS.md T23.
 */

export type SubmissionStatus =
  | "draft"
  | "submitted"
  | "submitted_with_exceptions"
  | "under_review"
  | "accepted"
  | "query_raised"
  | "escalated";

export interface BlockerDetail {
  flag_id: number | null;
  rule_code: string;
  level: "error" | "exception" | "warning";
  message: string;
  fix_hint?: string | null;
  field?: string | null;
  student_id?: number | null;
  student_name?: string | null;
  apaar_id?: string | null;
  enrolment_no?: string | null;
  course_id?: number | null;
  course_name?: string | null;
  target_link: string;
  reason: string;
}

export interface SubmissionGateResponse {
  institution_id: number;
  institution_name: string;
  aicte_id: string;
  academic_year: string;
  current_status: SubmissionStatus;
  is_locked: boolean;
  can_submit: boolean;
  target_status: "submitted" | "submitted_with_exceptions" | null;
  gate_reason: string;
  blockers: BlockerDetail[];
  total_students: number;
  total_courses: number;
  open_errors_count: number;
  unjustified_exceptions_count: number;
  unjustified_warnings_count: number;
  justified_exceptions_count: number;
  justified_warnings_count: number;
  seat_mismatch_detected: boolean;
  submission_id?: number | null;
  receipt_no?: string | null;
  submitted_at?: string | null;
  submitted_by_name?: string | null;
  declaration_ref?: string | null;
}

export interface SubmissionOtpRequest {
  academic_year: string;
}

export interface SubmissionOtpResponse {
  status: string;
  recipient: string;
  channel: string;
  purpose: string;
  expires_in: number;
  message: string;
}

export interface SubmissionSubmitRequest {
  academic_year: string;
  confirmed_declaration: boolean;
  declaration_text: string;
  otp_code: string;
}

export interface SubmissionReceiptResponse {
  institution_id: number;
  institution_name: string;
  aicte_id: string;
  academic_year: string;
  submission_id: number;
  receipt_no: string;
  status: "submitted" | "submitted_with_exceptions";
  submitted_at: string;
  submitted_by_email: string;
  submitted_by_name?: string | null;
  declaration_text: string;
  total_students: number;
  regular_students: number;
  supernumerary_students: number;
  courses_count: number;
  justified_exceptions_count: number;
  is_locked: boolean;
}
