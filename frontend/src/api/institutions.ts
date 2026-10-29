import { api, apiClient } from "./client";

export interface ActivationInitiateResponse {
  aicte_id: string;
  institution_name: string;
  masked_email: string;
  masked_phone: string;
  status: string;
  message: string;
}

export interface ActivationOtpVerifyResponse {
  verified: boolean;
  activation_token: string;
  aicte_id: string;
  institution_name: string;
  head_name: string;
  message: string;
}

export interface ActivationSubmitRequest {
  activation_token: string;
  signatory_name: string;
  signatory_ref: string;
  letter_content_b64?: string;
  letter_filename?: string;
}

export interface ActivationRequestResponse {
  id: number;
  institution_id: number;
  institution_aicte_id: string;
  institution_name: string;
  signatory_name: string;
  signatory_ref: string;
  letter_ref: string;
  status: "pending_approval" | "approved" | "rejected" | string;
  decided_by: number | null;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActivationStatusResponse {
  aicte_id: string;
  institution_name: string;
  account_status: "not_activated" | "pending_approval" | "active" | string;
  approval_status: "active" | "suspended" | "withdrawn" | "expired" | string;
  has_pending_request: boolean;
  latest_request_status: string | null;
  latest_request_id: number | null;
}

export interface ActivationDecisionResponse {
  request_id: number;
  institution_id: number;
  status: "approved" | "rejected";
  institution_account_status: string;
  admin_user_id: number | null;
  admin_email: string | null;
  initial_password: string | null;
  mfa_enabled: boolean;
  mfa_secret: string | null;
  mfa_uri: string | null;
  message: string;
}

export interface InstitutionResponse {
  id: number;
  aicte_id: string;
  name: string;
  state: string;
  district: string;
  address: string;
  official_email: string;
  official_phone: string;
  head_name: string;
  affiliating_university: string;
  approval_status: "active" | "suspended" | "withdrawn" | "expired" | string;
  approval_valid_to: string | null;
  account_status: "not_activated" | "pending_approval" | "active" | string;
  created_at: string;
  updated_at: string;
}

export interface InstitutionListResponse {
  total: number;
  items: InstitutionResponse[];
}

export interface CourseIntakeResponse {
  id: number;
  course_id: number;
  academic_year: string;
  approved_intake: number;
  supernumerary_seats_allowed: number;
  source: string;
  set_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface CourseIntakeHistoryResponse {
  id: number;
  course_id: number;
  academic_year: string;
  approved_intake: number;
  supernumerary_seats_allowed: number;
  source: string;
  set_by: string | null;
  change_reason: string | null;
  created_at: string;
}

export interface CourseResponse {
  id: number;
  institution_id: number;
  name: string;
  level: "UG" | "PG" | "Diploma" | "PGDM" | string;
  branch: string;
  duration_years: number;
  supernumerary_allowed: boolean;
  intakes: CourseIntakeResponse[];
  created_at: string;
  updated_at: string;
}

export interface DevOutboxMessage {
  id?: number;
  recipient: string;
  channel: string;
  body: string;
  created_at: string;
}

// Activation API Methods

export async function initiateActivation(aicteId: string): Promise<ActivationInitiateResponse> {
  return api.post<ActivationInitiateResponse>("/api/v1/institutions/activation/initiate", {
    aicte_id: aicteId.trim(),
  });
}

export async function verifyActivationOtp(
  aicteId: string,
  otpCode: string,
): Promise<ActivationOtpVerifyResponse> {
  return api.post<ActivationOtpVerifyResponse>("/api/v1/institutions/activation/verify-otp", {
    aicte_id: aicteId.trim(),
    otp_code: otpCode.trim(),
  });
}

export async function submitActivationJson(
  payload: ActivationSubmitRequest,
): Promise<ActivationRequestResponse> {
  return api.post<ActivationRequestResponse>("/api/v1/institutions/activation/submit", payload);
}

export async function submitActivationMultipart(
  formData: FormData,
): Promise<ActivationRequestResponse> {
  return apiClient<ActivationRequestResponse>("/api/v1/institutions/activation/submit-form", {
    method: "POST",
    body: formData,
  });
}

export async function getActivationStatus(aicteId: string): Promise<ActivationStatusResponse> {
  return api.get<ActivationStatusResponse>(
    `/api/v1/institutions/activation/status/${encodeURIComponent(aicteId.trim())}`,
  );
}

// AICTE Approvals Queue Methods

export async function listActivationRequests(
  status?: string,
  limit = 50,
  offset = 0,
): Promise<ActivationRequestResponse[]> {
  const query = new URLSearchParams();
  if (status && status !== "all") query.set("status", status);
  query.set("limit", String(limit));
  query.set("offset", String(offset));
  return api.get<ActivationRequestResponse[]>(
    `/api/v1/institutions/activation/requests?${query.toString()}`,
  );
}

export async function getActivationRequest(requestId: number): Promise<ActivationRequestResponse> {
  return api.get<ActivationRequestResponse>(`/api/v1/institutions/activation/requests/${requestId}`);
}

export async function approveActivation(
  requestId: number,
  data?: { admin_email?: string; notes?: string },
): Promise<ActivationDecisionResponse> {
  return api.post<ActivationDecisionResponse>(
    `/api/v1/institutions/activation/requests/${requestId}/approve`,
    data || {},
  );
}

export async function rejectActivation(
  requestId: number,
  data: { reason: string },
): Promise<ActivationDecisionResponse> {
  return api.post<ActivationDecisionResponse>(
    `/api/v1/institutions/activation/requests/${requestId}/reject`,
    data,
  );
}

// Institutions & Intake Management Methods

export async function listInstitutions(params?: {
  state?: string;
  approval_status?: string;
  account_status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<InstitutionListResponse> {
  const query = new URLSearchParams();
  if (params?.state) query.set("state", params.state);
  if (params?.approval_status && params.approval_status !== "all")
    query.set("approval_status", params.approval_status);
  if (params?.account_status && params.account_status !== "all")
    query.set("account_status", params.account_status);
  if (params?.search) query.set("search", params.search);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));

  const qs = query.toString();
  return api.get<InstitutionListResponse>(`/api/v1/institutions${qs ? `?${qs}` : ""}`);
}

export async function getInstitution(institutionId: number): Promise<InstitutionResponse> {
  return api.get<InstitutionResponse>(`/api/v1/institutions/${institutionId}`);
}

export async function updateInstitutionApprovalStatus(
  institutionId: number,
  data: {
    approval_status: string;
    approval_valid_to?: string | null;
    reason?: string;
  },
): Promise<InstitutionResponse> {
  return api.patch<InstitutionResponse>(
    `/api/v1/institutions/${institutionId}/approval-status`,
    data,
  );
}

export async function listCourses(institutionId: number): Promise<CourseResponse[]> {
  return api.get<CourseResponse[]>(`/api/v1/institutions/${institutionId}/courses`);
}

export async function getCourseIntakes(
  institutionId: number,
  courseId: number,
  academicYear?: string,
): Promise<CourseIntakeResponse[]> {
  const query = academicYear ? `?academic_year=${encodeURIComponent(academicYear)}` : "";
  return api.get<CourseIntakeResponse[]>(
    `/api/v1/institutions/${institutionId}/courses/${courseId}/intake${query}`,
  );
}

export async function updateCourseIntake(
  institutionId: number,
  courseId: number,
  data: {
    academic_year: string;
    approved_intake: number;
    supernumerary_seats_allowed?: number;
    change_reason?: string;
  },
): Promise<CourseIntakeResponse> {
  return api.put<CourseIntakeResponse>(
    `/api/v1/institutions/${institutionId}/courses/${courseId}/intake`,
    data,
  );
}

export async function getIntakeHistory(
  institutionId: number,
  courseId: number,
  academicYear?: string,
): Promise<CourseIntakeHistoryResponse[]> {
  const query = academicYear ? `?academic_year=${encodeURIComponent(academicYear)}` : "";
  return api.get<CourseIntakeHistoryResponse[]>(
    `/api/v1/institutions/${institutionId}/courses/${courseId}/intake/history${query}`,
  );
}

export async function getDevOutbox(): Promise<DevOutboxMessage[]> {
  return api.get<DevOutboxMessage[]>("/api/v1/dev/outbox");
}

export interface NotificationItem {
  id: number;
  institution_id: number;
  type: string;
  payload: Record<string, any>;
  read_at: string | null;
  created_at: string | null;
}

export async function getInstitutionNotifications(
  institutionId: number,
  limit: number = 50,
): Promise<NotificationItem[]> {
  return api.get<NotificationItem[]>(
    `/api/v1/institutions/${institutionId}/notifications?limit=${limit}`,
  );
}

export async function markNotificationRead(
  institutionId: number,
  notificationId: number,
): Promise<{ status: string; id: number; read_at: string | null }> {
  return api.patch<{ status: string; id: number; read_at: string | null }>(
    `/api/v1/institutions/${institutionId}/notifications/${notificationId}/read`,
    {},
  );
}

export async function markAllNotificationsRead(
  institutionId: number,
): Promise<{ status: string; marked_read_count: number }> {
  return api.post<{ status: string; marked_read_count: number }>(
    `/api/v1/institutions/${institutionId}/notifications/mark-all-read`,
    {},
  );
}
