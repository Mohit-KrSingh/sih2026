/**
 * Types for AICTE Analytics, Monitoring, and Compliance.
 * Spec: Section 10, 12 & TASKS.md T28, T29
 */

export interface SubmissionProgressCounts {
  submitted_clean: number;
  submitted_with_exceptions: number;
  under_review: number;
  accepted: number;
  query_raised: number;
  escalated: number;
  draft: number;
  not_started: number;
  total_eligible: number;
}

export interface OverviewMetrics {
  academic_year: string;
  total_colleges: number;
  active_colleges: number;
  pending_activation_colleges: number;
  total_students_enrolled: number;
  total_approved_intake: number;
  total_supernumerary_intake: number;
  total_courses: number;
  total_errors: number;
  total_exceptions: number;
  total_warnings: number;
  total_infos: number;
  total_duplicate_cases: number;
  total_anomalies_flagged: number;
  over_intake_violations_count: number;
  submission_progress: SubmissionProgressCounts;
}

export interface ComplianceViolation {
  institution_id: number;
  aicte_id: string;
  institution_name: string;
  state: string;
  course_id: number;
  course_name: string;
  level: string;
  approved_intake: number;
  regular_admitted: number;
  overshoot: number;
  supernumerary_allowed: number;
  supernumerary_admitted: number;
  is_red_list: boolean;
  submission_status: string | null;
  last_updated: string | null;
}

export interface ComplianceListResponse {
  academic_year: string;
  total_violations: number;
  red_list_colleges_count: number;
  violations: ComplianceViolation[];
}

export interface StateMetricsItem {
  state: string;
  colleges_count: number;
  approved_intake: number;
  regular_admitted: number;
  supernumerary_admitted: number;
  total_enrolled: number;
  utilization_rate: number;
  over_intake_colleges: number;
  exceptions_count: number;
  duplicates_count: number;
  submissions_completed: number;
}

export interface CourseMetricsItem {
  course_name: string;
  level: string;
  total_courses: number;
  colleges_count: number;
  approved_intake: number;
  regular_admitted: number;
  supernumerary_admitted: number;
  total_enrolled: number;
  utilization_rate: number;
  over_intake_violations: number;
}

export interface DuplicateCollegeRef {
  institution_id: number;
  institution_name: string;
  aicte_id: string;
  course_name: string;
  status: string;
}

export interface DuplicateRecord {
  apaar_id: string;
  student_name: string;
  academic_year: string;
  colleges: DuplicateCollegeRef[];
  rule_code: string;
  level: string;
  status: string;
}

export interface DuplicateListResponse {
  total_duplicates: number;
  academic_year?: string;
  items: DuplicateRecord[];
}

export interface AnomalyScoreItem {
  id: number;
  institution_id: number;
  institution_name: string | null;
  aicte_id: string | null;
  course_id: number;
  course_name: string | null;
  academic_year: string;
  score: number;
  flagged: boolean;
  features: Record<string, any>;
  summary: string | null;
  created_at: string | null;
}

export interface AnomalyScoreListResponse {
  total: number;
  flagged_count: number;
  academic_year?: string;
  items: AnomalyScoreItem[];
}

export interface DrilldownStudentFlag {
  id: number;
  rule_code: string;
  level: string;
  message: string;
  fix_hint: string | null;
  status: string;
}

export interface DrilldownStudent {
  id: number;
  apaar_id: string;
  name: string;
  gender: string;
  enrolment_no: string;
  admission_mode: string;
  seat_type: string;
  reservation_category: string;
  status: string;
  flags: DrilldownStudentFlag[];
}

export interface DrilldownCourse {
  course_id: number;
  name: string;
  level: string;
  branch: string;
  approved_intake: number;
  regular_admitted: number;
  supernumerary_allowed: number;
  supernumerary_admitted: number;
  overshoot: number;
  flagged_students_count: number;
}

export interface DrilldownCollege {
  institution_id: number;
  name: string;
  aicte_id: string;
  state: string;
  district: string | null;
  approved_intake: number;
  regular_admitted: number;
  overshoot: number;
  total_flags: number;
  submission_status: string | null;
}

export interface DrilldownState {
  state: string;
  colleges_count: number;
  total_enrolled: number;
  approved_intake: number;
  overshoot: number;
  over_intake_colleges: number;
}

export interface DrilldownResponse {
  academic_year: string;
  level: "national" | "state" | "college" | "course";
  state: string | null;
  institution: DrilldownCollege | null;
  course: DrilldownCourse | null;
  states: DrilldownState[];
  colleges: DrilldownCollege[];
  courses: DrilldownCourse[];
  students: DrilldownStudent[];
}

export interface SendNoticeRequest {
  institution_id: number;
  subject: string;
  message: string;
  urgency?: "normal" | "warning" | "urgent";
}

export interface NoticeResponse {
  success: boolean;
  notification_id: number;
  recipient_institution_id: number;
  subject: string;
  sent_at: string;
}

export interface ResolveFlagRequest {
  flag_id: number;
  note: string;
  action: "resolve" | "dismiss";
}

export interface ResolveFlagResponse {
  success: boolean;
  flag_id: number;
  status: string;
  student_id: number | null;
  student_status: string | null;
  resolved_at: string;
}

export interface SSEEventPayload {
  id: string;
  event: string;
  data: any;
  timestamp: string;
}
