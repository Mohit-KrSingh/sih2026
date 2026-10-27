import { api } from "./client";

export interface ValidationFlagSummary {
  rule_code: string;
  level: "error" | "exception" | "warning" | "info";
  message: string;
  fix_hint?: string | null;
  field?: string | null;
}

export interface CourseSummaryResponse {
  course_id: number;
  course_name: string;
  branch: string;
  level: string;
  duration_years: number;
  academic_year: string;
  approved_intake: number;
  supernumerary_seats_allowed: number;
  regular_admitted: number;
  supernumerary_admitted: number;
  nri_count: number;
  oci_count: number;
  fn_count: number;
  total_declared: number;
  calculated_enrolment: number;
  calculated_regular: number;
  calculated_supernumerary: number;
  status: "draft" | "declared" | "locked" | string;
  status_badge: "within_limit" | "over_by_n";
  overshoot: number;
  supernumerary_overshoot: number;
  flags: ValidationFlagSummary[];
  updated_at?: string | null;
}

export interface InstitutionSeatDeclarationResponse {
  institution_id: number;
  academic_year: string;
  total_approved_intake: number;
  total_supernumerary_allowed: number;
  total_declared_regular: number;
  total_declared_supernumerary: number;
  total_declared: number;
  total_enrolled: number;
  courses: CourseSummaryResponse[];
}

export interface SeatDeclarationSaveRequest {
  academic_year: string;
  regular_admitted: number;
  supernumerary_admitted: number;
  nri_count?: number;
  oci_count?: number;
  fn_count?: number;
  status?: "draft" | "declared";
}

export interface SeatDeclarationBatchItem {
  course_id: number;
  regular_admitted: number;
  supernumerary_admitted: number;
  nri_count?: number;
  oci_count?: number;
  fn_count?: number;
  status?: "draft" | "declared";
}

export interface SeatDeclarationBatchSaveRequest {
  academic_year: string;
  declarations: SeatDeclarationBatchItem[];
}

export async function getInstitutionSeatDeclarations(
  institutionId: number,
  academicYear: string = "2026-27",
): Promise<InstitutionSeatDeclarationResponse> {
  const query = academicYear ? `?academic_year=${encodeURIComponent(academicYear)}` : "";
  return api.get<InstitutionSeatDeclarationResponse>(
    `/api/v1/institutions/${institutionId}/seat-declarations${query}`,
  );
}

export async function getCourseSummary(
  institutionId: number,
  courseId: number,
  academicYear: string = "2026-27",
): Promise<CourseSummaryResponse> {
  const query = academicYear ? `?academic_year=${encodeURIComponent(academicYear)}` : "";
  return api.get<CourseSummaryResponse>(
    `/api/v1/institutions/${institutionId}/courses/${courseId}/seat-declaration${query}`,
  );
}

export async function saveCourseSeatDeclaration(
  institutionId: number,
  courseId: number,
  data: SeatDeclarationSaveRequest,
): Promise<CourseSummaryResponse> {
  return api.put<CourseSummaryResponse>(
    `/api/v1/institutions/${institutionId}/courses/${courseId}/seat-declaration`,
    data,
  );
}

export async function batchSaveSeatDeclarations(
  institutionId: number,
  data: SeatDeclarationBatchSaveRequest,
): Promise<InstitutionSeatDeclarationResponse> {
  return api.put<InstitutionSeatDeclarationResponse>(
    `/api/v1/institutions/${institutionId}/seat-declarations`,
    data,
  );
}
