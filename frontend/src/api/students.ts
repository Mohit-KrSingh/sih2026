/**
 * Typed API client for student records and directory management.
 * Spec: 8.2, 9.4, 13 & TASKS.md T20
 */

import { api } from "./client";

export interface StudentValidationFlag {
  id?: number | null;
  rule_code: string;
  level: "error" | "exception" | "warning" | "info";
  field?: string | null;
  message: string;
  fix_hint?: string | null;
  audience?: string;
  requires_justification?: boolean;
  status?: string;
}

export interface StudentResponse {
  id: number;
  institution_id: number;
  course_id: number | null;
  course_name: string;
  branch: string;
  academic_year: string;
  apaar_id: string;
  name: string;
  dob: string;
  gender: string;
  enrolment_no: string;
  admission_date: string;
  admission_mode: string;
  seat_type: string;
  reservation_category: string;
  nri: string;
  oci: string;
  foreign_national: string;
  country?: string | null;
  status: string;
  is_locked: boolean;
  submission_id?: number | null;
  source: string;
  flags: StudentValidationFlag[];
  created_at: string;
  updated_at: string;
}

export interface StudentCreateRequest {
  apaar_id: string;
  name: string;
  dob: string;
  gender: string;
  course_id: number;
  academic_year?: string;
  enrolment_no: string;
  admission_date: string;
  admission_mode: string;
  seat_type: string;
  reservation_category: string;
  nri?: string;
  oci?: string;
  foreign_national?: string;
  country?: string | null;
  status?: string;
}

export interface StudentUpdateRequest {
  apaar_id?: string;
  name?: string;
  dob?: string;
  gender?: string;
  course_id?: number;
  academic_year?: string;
  enrolment_no?: string;
  admission_date?: string;
  admission_mode?: string;
  seat_type?: string;
  reservation_category?: string;
  nri?: string;
  oci?: string;
  foreign_national?: string;
  country?: string | null;
  status?: string;
}

export interface StudentSaveResultResponse {
  student: StudentResponse;
  flags: StudentValidationFlag[];
  is_valid: boolean;
  errors_count: number;
  exceptions_count: number;
  warnings_count: number;
  infos_count: number;
}

export interface StudentListStats {
  total: number;
  valid: number;
  flagged: number;
  draft: number;
  submitted: number;
  error_flags_count: number;
  exception_flags_count: number;
  warning_flags_count: number;
}

export interface StudentListResponse {
  items: StudentResponse[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  stats: StudentListStats;
}

export interface StudentFilterParams {
  academic_year?: string;
  course_id?: number;
  status?: string;
  level?: string;
  search?: string;
  page?: number;
  limit?: number;
}

/**
 * Fetch filtered, paginated students list for an institution.
 */
export async function getStudents(
  institutionId: number,
  params?: StudentFilterParams
): Promise<StudentListResponse> {
  const query = new URLSearchParams();
  if (params?.academic_year) query.append("academic_year", params.academic_year);
  if (params?.course_id) query.append("course_id", params.course_id.toString());
  if (params?.status && params.status !== "all") query.append("status", params.status);
  if (params?.level && params.level !== "all") query.append("level", params.level);
  if (params?.search) query.append("search", params.search);
  if (params?.page) query.append("page", params.page.toString());
  if (params?.limit) query.append("limit", params.limit.toString());

  const queryString = query.toString();
  const endpoint = `/api/v1/institutions/${institutionId}/students${
    queryString ? `?${queryString}` : ""
  }`;
  return api.get<StudentListResponse>(endpoint);
}

/**
 * Fetch a single student record with decrypted data and active flags.
 */
export async function getStudent(
  institutionId: number,
  studentId: number
): Promise<StudentResponse> {
  return api.get<StudentResponse>(
    `/api/v1/institutions/${institutionId}/students/${studentId}`
  );
}

/**
 * Create a new student draft record and execute validation engine ("Check and save").
 */
export async function createStudent(
  institutionId: number,
  data: StudentCreateRequest
): Promise<StudentSaveResultResponse> {
  return api.post<StudentSaveResultResponse>(
    `/api/v1/institutions/${institutionId}/students`,
    data
  );
}

/**
 * Update an existing student draft record and re-execute validation engine ("Check and save").
 */
export async function updateStudent(
  institutionId: number,
  studentId: number,
  data: StudentUpdateRequest
): Promise<StudentSaveResultResponse> {
  return api.put<StudentSaveResultResponse>(
    `/api/v1/institutions/${institutionId}/students/${studentId}`,
    data
  );
}

/**
 * Delete a student draft record.
 */
export async function deleteStudent(
  institutionId: number,
  studentId: number
): Promise<{ message: string; student_id: number }> {
  return api.delete<{ message: string; student_id: number }>(
    `/api/v1/institutions/${institutionId}/students/${studentId}`
  );
}

// Bulk Upload Types & Functions (Spec 8.2, 9.4, 13 & TASKS.md T21)

export interface UploadSummary {
  total_rows: number;
  valid_rows: number;
  flagged_rows: number;
  error_count: number;
  exception_count: number;
  warning_count: number;
  info_count: number;
  inserted_count: number;
  updated_count: number;
}

export interface UploadRowResult {
  row_number: number;
  student_id?: number | null;
  apaar_id: string;
  name: string;
  dob: string;
  gender: string;
  course: string;
  branch: string;
  admission_year: string;
  enrolment_no: string;
  admission_date: string;
  admission_mode: string;
  seat_type: string;
  reservation_category: string;
  nri: string;
  oci: string;
  foreign_national: string;
  country?: string | null;
  status: string;
  flags: StudentValidationFlag[];
}

export interface UploadResultResponse {
  upload_id: number;
  filename: string;
  row_count: number;
  summary: UploadSummary;
  rows: UploadRowResult[];
}

export interface UploadHistoryItem {
  id: number;
  institution_id: number;
  filename: string;
  row_count: number;
  status: string;
  summary_json?: {
    summary?: UploadSummary;
    errors?: Array<{
      row_number: number;
      field: string;
      rule_code: string;
      level: string;
      message: string;
      fix_hint: string;
    }>;
  } | null;
  uploaded_by?: number | null;
  created_at: string;
}

export interface UploadHistoryResponse {
  items: UploadHistoryItem[];
  total: number;
}

/**
 * Download canonical student upload CSV template.
 */
export async function downloadTemplateCsv(institutionId: number): Promise<string> {
  const token = localStorage.getItem("apaar_access_token");
  const base = import.meta.env.VITE_API_BASE_URL || "";
  const res = await fetch(`${base}/api/v1/institutions/${institutionId}/students/upload/template`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    throw new Error(`Failed to download template: ${res.statusText}`);
  }
  return res.text();
}

/**
 * Upload bulk student file (CSV/Excel) and execute validation engine.
 */
export async function uploadStudentsFile(
  institutionId: number,
  file: File,
  academicYear: string = "2026-27"
): Promise<UploadResultResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("academic_year", academicYear);

  return api.post<UploadResultResponse>(
    `/api/v1/institutions/${institutionId}/students/upload`,
    formData
  );
}

/**
 * Retrieve bulk student upload history for an institution.
 */
export async function getUploadHistory(
  institutionId: number,
  limit: number = 20,
  offset: number = 0
): Promise<UploadHistoryResponse> {
  return api.get<UploadHistoryResponse>(
    `/api/v1/institutions/${institutionId}/students/uploads?limit=${limit}&offset=${offset}`
  );
}

/**
 * Retrieve past upload details and row evaluation flags.
 */
export async function getUploadDetails(
  institutionId: number,
  uploadId: number
): Promise<UploadResultResponse> {
  return api.get<UploadResultResponse>(
    `/api/v1/institutions/${institutionId}/students/uploads/${uploadId}`
  );
}

/**
 * Download CSV error file for an upload.
 */
export async function downloadErrorCsv(
  institutionId: number,
  uploadId: number
): Promise<string> {
  const token = localStorage.getItem("apaar_access_token");
  const base = import.meta.env.VITE_API_BASE_URL || "";
  const res = await fetch(
    `${base}/api/v1/institutions/${institutionId}/students/uploads/${uploadId}/errors`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to download error file: ${res.statusText}`);
  }
  return res.text();
}
