import { apiClient, getStoredToken } from "./client";
import type {
  InstitutionFlagsListResponse,
  Justification,
  ValidationFlagDetail,
} from "../types/validation";

export interface FlagQueryFilters {
  academic_year?: string;
  level?: string;
  status?: string;
  rule_code?: string;
  course_id?: number;
  student_id?: number;
  requires_justification?: boolean;
  search?: string;
}

/**
 * Fetch validation flags for an institution with statistical summary and filters.
 */
export async function getInstitutionFlags(
  institutionId: number,
  filters: FlagQueryFilters = {}
): Promise<InstitutionFlagsListResponse> {
  const params = new URLSearchParams();
  if (filters.academic_year) params.append("academic_year", filters.academic_year);
  if (filters.level) params.append("level", filters.level);
  if (filters.status) params.append("status", filters.status);
  if (filters.rule_code) params.append("rule_code", filters.rule_code);
  if (filters.course_id) params.append("course_id", String(filters.course_id));
  if (filters.student_id) params.append("student_id", String(filters.student_id));
  if (filters.requires_justification !== undefined) {
    params.append("requires_justification", String(filters.requires_justification));
  }
  if (filters.search) params.append("search", filters.search);

  const qs = params.toString() ? `?${params.toString()}` : "";
  return apiClient<InstitutionFlagsListResponse>(
    `/api/v1/institutions/${institutionId}/flags${qs}`
  );
}

/**
 * Fetch single validation flag detail and justification history.
 */
export async function getFlagDetail(
  institutionId: number,
  flagId: number
): Promise<ValidationFlagDetail> {
  return apiClient<ValidationFlagDetail>(
    `/api/v1/institutions/${institutionId}/flags/${flagId}`
  );
}

/**
 * Submit written justification and optional supporting document for an exception or warning flag.
 */
export async function createJustification(
  institutionId: number,
  flagId: number,
  text: string,
  documentFile?: File | null
): Promise<Justification> {
  const formData = new FormData();
  formData.append("text", text);
  if (documentFile) {
    formData.append("document", documentFile);
  }

  return apiClient<Justification>(
    `/api/v1/institutions/${institutionId}/flags/${flagId}/justifications`,
    {
      method: "POST",
      body: formData,
    }
  );
}

/**
 * Download attached justification supporting document.
 */
export async function downloadJustificationDocument(
  institutionId: number,
  justificationId: number
): Promise<{ blob: Blob; filename: string }> {
  const token = getStoredToken();
  const url = `/api/v1/institutions/${institutionId}/justifications/${justificationId}/document`;

  const headers: HeadersInit = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new Error(`Failed to download document (${response.status})`);
  }

  let filename = "supporting_document.pdf";
  const disposition = response.headers.get("content-disposition");
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const blob = await response.blob();
  return { blob, filename };
}

/**
 * Delete an existing justification before final submission.
 */
export async function deleteJustification(
  institutionId: number,
  justificationId: number
): Promise<{ message: string; flag_id: number; flag_status: string }> {
  return apiClient<{ message: string; flag_id: number; flag_status: string }>(
    `/api/v1/institutions/${institutionId}/justifications/${justificationId}`,
    {
      method: "DELETE",
    }
  );
}
