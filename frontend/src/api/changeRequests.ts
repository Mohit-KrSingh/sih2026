import { api, apiClient } from "./client";
import type {
  ChangeRequest,
  ChangeRequestCreatePayload,
  ChangeRequestDecisionPayload,
  ChangeRequestListResponse,
} from "../types/changeRequests";

/**
 * Fetch change requests for a specific institution.
 */
export async function getInstitutionChangeRequests(
  institutionId: number,
  params?: {
    status?: string;
    academic_year?: string;
    student_id?: number;
    limit?: number;
    offset?: number;
  }
): Promise<ChangeRequestListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.append("status", params.status);
  if (params?.academic_year) query.append("academic_year", params.academic_year);
  if (params?.student_id) query.append("student_id", String(params.student_id));
  if (params?.limit) query.append("limit", String(params.limit));
  if (params?.offset) query.append("offset", String(params.offset));

  const qs = query.toString() ? `?${query.toString()}` : "";
  return api.get<ChangeRequestListResponse>(
    `/api/v1/institutions/${institutionId}/change-requests${qs}`
  );
}

/**
 * Fetch details of a single change request for an institution.
 */
export async function getInstitutionChangeRequest(
  institutionId: number,
  requestId: number
): Promise<ChangeRequest> {
  return api.get<ChangeRequest>(
    `/api/v1/institutions/${institutionId}/change-requests/${requestId}`
  );
}

/**
 * Submit a new change request with reason and evidence file.
 */
export async function submitChangeRequest(
  institutionId: number,
  payload: ChangeRequestCreatePayload
): Promise<ChangeRequest> {
  const formData = new FormData();
  formData.append("student_id", String(payload.student_id));
  formData.append("field", payload.field);
  formData.append("new_value", payload.new_value);
  formData.append("reason", payload.reason);
  if (payload.document) {
    formData.append("document", payload.document);
  }
  if (payload.document_ref) {
    formData.append("document_ref", payload.document_ref);
  }

  return apiClient<ChangeRequest>(
    `/api/v1/institutions/${institutionId}/change-requests`,
    {
      method: "POST",
      body: formData,
    }
  );
}

/**
 * Get download URL for an institution's change request evidence document.
 */
export function getInstitutionChangeRequestEvidenceUrl(
  institutionId: number,
  requestId: number
): string {
  return `/api/v1/institutions/${institutionId}/change-requests/${requestId}/evidence`;
}

/**
 * AICTE: List change requests across all institutions.
 */
export async function getAicteChangeRequests(params?: {
  status?: string;
  institution_id?: number;
  academic_year?: string;
  student_id?: number;
  limit?: number;
  offset?: number;
}): Promise<ChangeRequestListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.append("status", params.status);
  if (params?.institution_id) query.append("institution_id", String(params.institution_id));
  if (params?.academic_year) query.append("academic_year", params.academic_year);
  if (params?.student_id) query.append("student_id", String(params.student_id));
  if (params?.limit) query.append("limit", String(params.limit));
  if (params?.offset) query.append("offset", String(params.offset));

  const qs = query.toString() ? `?${query.toString()}` : "";
  return api.get<ChangeRequestListResponse>(`/api/v1/change-requests${qs}`);
}

/**
 * AICTE: Get change request detail across any institution.
 */
export async function getAicteChangeRequest(requestId: number): Promise<ChangeRequest> {
  return api.get<ChangeRequest>(`/api/v1/change-requests/${requestId}`);
}

/**
 * AICTE: Approve or reject a student change request.
 */
export async function decideAicteChangeRequest(
  requestId: number,
  payload: ChangeRequestDecisionPayload
): Promise<ChangeRequest> {
  return api.post<ChangeRequest>(`/api/v1/change-requests/${requestId}/decision`, payload);
}

/**
 * AICTE: Get download URL for change request evidence document.
 */
export function getAicteChangeRequestEvidenceUrl(requestId: number): string {
  return `/api/v1/change-requests/${requestId}/evidence`;
}
