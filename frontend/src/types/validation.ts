export type FlagLevel = "error" | "exception" | "warning" | "info";

export type FlagStatus = "open" | "justified" | "resolved" | "dismissed";

export interface ValidationFlag {
  id?: number;
  rule_code: string;
  level: FlagLevel;
  message: string;
  field_name?: string | null;
  row_number?: number | null;
  fix_hint?: string | null;
  status?: string;
  justification?: string | null;
}

export interface Justification {
  id: number;
  flag_id: number;
  text: string;
  document_ref?: string | null;
  document_url?: string | null;
  by_user?: number | null;
  author_name?: string | null;
  author_role?: string | null;
  at: string;
  created_at: string;
  updated_at: string;
}

export interface FlagTargetStudent {
  id: number;
  apaar_id: string;
  name: string;
  enrolment_no: string;
  academic_year: string;
  course_name?: string | null;
  branch?: string | null;
}

export interface FlagTargetCourse {
  id: number;
  name: string;
  branch: string;
  level: string;
}

export interface ValidationFlagDetail {
  id: number;
  student_id?: number | null;
  course_id?: number | null;
  submission_id?: number | null;
  rule_code: string;
  level: FlagLevel;
  field?: string | null;
  message: string;
  fix_hint?: string | null;
  audience: string;
  requires_justification: boolean;
  status: FlagStatus;
  student?: FlagTargetStudent | null;
  course?: FlagTargetCourse | null;
  justifications: Justification[];
  created_at: string;
  updated_at: string;
}

export interface ValidationFlagsSummary {
  total_flags: number;
  open_count: number;
  justified_count: number;
  resolved_count: number;
  error_count: number;
  exception_count: number;
  warning_count: number;
  info_count: number;
  blocking_count: number;
  can_submit: boolean;
}

export interface InstitutionFlagsListResponse {
  institution_id: number;
  academic_year?: string | null;
  summary: ValidationFlagsSummary;
  items: ValidationFlagDetail[];
}
