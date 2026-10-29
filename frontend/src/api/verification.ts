import { api } from "./client";

export interface VerificationResult {
  verified: boolean;
  status: "ready" | "active" | "revoked" | "tampered" | "not_found" | "invalid_query";
  verification_id?: string;
  message?: string;
  verified_by?: string;
  institution?: string;
  course?: string;
  years?: string;
  student_status?: string;
  issued_at?: string;
  signature_preview?: string;
  revocation_reason?: string;
}

export interface VerificationRecordProof {
  verification_id: string;
  status: string;
  issued_at: string;
  signature: string;
  verified: boolean;
  issued_by: string;
}

export interface PublicKeyResponse {
  algorithm: string;
  public_key_hex: string;
  issuer: string;
  description: string;
}

export interface VerifierProfile {
  id: number;
  org_name: string;
  org_type: "employer" | "regulator" | "institution" | string;
  contact: string;
  status: "pending" | "approved" | "revoked";
  created_at: string;
  updated_at: string;
}

export interface ConsentRequestItem {
  id: number;
  verifier_id: number;
  verifier_name: string;
  verifier_type: string;
  apaar_id: string;
  status: "pending" | "approved" | "denied" | "expired" | "used";
  purpose: string;
  scope_fields: string[];
  requested_at: string;
  decided_at?: string | null;
  expires_at: string;
  is_expired: boolean;
  is_used: boolean;
}

export interface ConsentRequestListResponse {
  items: ConsentRequestItem[];
  total: number;
}

export interface ConsentedStudentRecord {
  institution: string;
  course: string;
  years: string;
  status: string;
  verification_id: string;
  verified_by: string;
  verified: boolean;
  purpose: string;
  accessed_at: string;
  consent_request_id: number;
  verifier_name: string;
  message: string;
}

export interface StudentOtpSendResponse {
  status: string;
  apaar_id: string;
  channel: string;
  expires_in: number;
  message: string;
}

export interface StudentTokenResponse {
  access_token: string;
  token_type: string;
  apaar_id: string;
  student_name?: string | null;
  expires_in_hours: number;
}

export interface StudentAcademicRecord {
  student_id?: number | null;
  enrolment_no?: string | null;
  institution_id: number;
  institution_name: string;
  institution_aicte_id: string;
  course_id?: number | null;
  course_name: string;
  academic_year: string;
  status: string;
  verification_id?: string | null;
  issued_at?: string | null;
}

export interface StudentRecordsListResponse {
  apaar_id: string;
  records: StudentAcademicRecord[];
  total: number;
}

export interface DevOutboxMessage {
  id: number;
  channel: string;
  recipient: string;
  body: string;
  context?: string | null;
  created_at: string;
}

// Public Verification & Proof Lookups (T32)

export async function verifyCredential(vid: string): Promise<VerificationResult> {
  return api.get<VerificationResult>(
    `/api/v1/verification/verify?vid=${encodeURIComponent(vid.trim())}`
  );
}

export async function getVerificationRecordProof(vid: string): Promise<VerificationRecordProof> {
  return api.get<VerificationRecordProof>(
    `/api/v1/verification/records/${encodeURIComponent(vid.trim())}`
  );
}

export function getVerificationQrUrl(vid: string): string {
  const base = (import.meta.env.VITE_API_BASE_URL as string) || "";
  return `${base}/api/v1/verification/records/${encodeURIComponent(vid.trim())}/qr`;
}

export async function getEd25519PublicKey(): Promise<PublicKeyResponse> {
  return api.get<PublicKeyResponse>("/api/v1/verification/public-key");
}

export async function revokeVerificationRecord(
  vid: string,
  reason: string
): Promise<{ status: string; verification_id: string; reason: string }> {
  return api.post(`/api/v1/verification/records/${encodeURIComponent(vid.trim())}/revoke`, {
    reason,
  });
}

// Verifier Portal APIs (T33 / T34)

export async function getMyVerifierProfile(): Promise<VerifierProfile> {
  return api.get<VerifierProfile>("/api/v1/verification/verifiers/me");
}

export async function createConsentRequest(
  apaar_id: string,
  purpose: string = "Pre-employment or academic background verification"
): Promise<ConsentRequestItem> {
  return api.post<ConsentRequestItem>("/api/v1/verification/consent-requests", {
    apaar_id: apaar_id.trim(),
    purpose: purpose.trim(),
  });
}

export async function getVerifierConsentRequests(status?: string): Promise<ConsentRequestListResponse> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return api.get<ConsentRequestListResponse>(`/api/v1/verification/consent-requests${query}`);
}

export async function getConsentRequestDetails(requestId: number): Promise<ConsentRequestItem> {
  return api.get<ConsentRequestItem>(`/api/v1/verification/consent-requests/${requestId}`);
}

export async function getConsentedRecord(requestId: number): Promise<ConsentedStudentRecord> {
  return api.get<ConsentedStudentRecord>(`/api/v1/verification/consent-requests/${requestId}/record`);
}

// Student Consent Portal APIs (T33 / T34)

export async function sendStudentOtp(apaarId: string): Promise<StudentOtpSendResponse> {
  return api.post<StudentOtpSendResponse>("/api/v1/verification/student/otp/send", {
    apaar_id: apaarId.trim(),
  });
}

export async function verifyStudentOtp(apaarId: string, otp: string): Promise<StudentTokenResponse> {
  return api.post<StudentTokenResponse>("/api/v1/verification/student/otp/verify", {
    apaar_id: apaarId.trim(),
    otp: otp.trim(),
  });
}

export async function getStudentAcademicRecords(studentToken: string): Promise<StudentRecordsListResponse> {
  return api.get<StudentRecordsListResponse>("/api/v1/verification/student/records", {
    token: studentToken,
  });
}

export async function getStudentConsentRequests(studentToken: string): Promise<ConsentRequestListResponse> {
  return api.get<ConsentRequestListResponse>("/api/v1/verification/student/consent-requests", {
    token: studentToken,
  });
}

export async function decideStudentConsent(
  studentToken: string,
  requestId: number,
  decision: "approved" | "denied"
): Promise<ConsentRequestItem> {
  return api.post<ConsentRequestItem>(
    `/api/v1/verification/student/consent-requests/${requestId}/decide`,
    { decision },
    { token: studentToken }
  );
}

// Dev Outbox Inspection Helper (Demo Mode)

export async function getDevOutbox(recipient?: string): Promise<DevOutboxMessage[]> {
  const query = recipient ? `?recipient=${encodeURIComponent(recipient.trim())}` : "";
  return api.get<DevOutboxMessage[]>(`/api/v1/dev/outbox${query}`);
}

// Degree Certificate PDF APIs (Spec 17, TASKS.md T35)

export function getStudentCertificateUrl(
  institutionId: number,
  studentId: number,
  download: boolean = false
): string {
  return `/api/v1/institutions/${institutionId}/students/${studentId}/certificate${download ? "?download=true" : ""}`;
}

export async function downloadStudentCertificate(
  institutionId: number,
  studentId: number,
  filename?: string
): Promise<void> {
  const url = getStudentCertificateUrl(institutionId, studentId, true);
  const token = localStorage.getItem("apaar_access_token");
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new Error(`Failed to download certificate: ${response.statusText}`);
  }

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = filename || `certificate_student_${studentId}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
}

export async function downloadStudentPortalCertificate(
  studentId: number,
  studentToken: string,
  filename?: string
): Promise<void> {
  const url = `/api/v1/verification/student/records/${studentId}/certificate?download=true`;
  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${studentToken}`,
    },
  });
  if (!response.ok) {
    throw new Error(`Failed to download certificate: ${response.statusText}`);
  }

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = filename || `certificate_student_${studentId}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
}
