import { apiClient } from "./client";
import type {
  SubmissionGateResponse,
  SubmissionOtpResponse,
  SubmissionReceiptResponse,
  SubmissionSubmitRequest,
} from "../types/submissions";

/**
 * Fetch submission gate readiness, blockers, and locking status for an institution.
 */
export async function getSubmissionGate(
  institutionId: number,
  academicYear: string = "2026-27"
): Promise<SubmissionGateResponse> {
  const params = new URLSearchParams({ academic_year: academicYear });
  return apiClient<SubmissionGateResponse>(
    `/api/v1/institutions/${institutionId}/submissions/gate?${params.toString()}`
  );
}

/**
 * Request a 6-digit verification OTP for the final submission declaration.
 */
export async function requestDeclarationOtp(
  institutionId: number,
  academicYear: string = "2026-27"
): Promise<SubmissionOtpResponse> {
  return apiClient<SubmissionOtpResponse>(
    `/api/v1/institutions/${institutionId}/submissions/declaration-otp`,
    {
      method: "POST",
      body: JSON.stringify({ academic_year: academicYear }),
    }
  );
}

/**
 * Submit and lock annual student data into the AICTE Central Repository.
 * Accessible exclusively to college_admin role.
 */
export async function submitAnnualData(
  institutionId: number,
  payload: SubmissionSubmitRequest
): Promise<SubmissionReceiptResponse> {
  return apiClient<SubmissionReceiptResponse>(
    `/api/v1/institutions/${institutionId}/submissions/submit`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

/**
 * Retrieve the official receipt for a completed annual submission.
 */
export async function getSubmissionReceipt(
  institutionId: number,
  academicYear: string = "2026-27"
): Promise<SubmissionReceiptResponse> {
  const params = new URLSearchParams({ academic_year: academicYear });
  return apiClient<SubmissionReceiptResponse>(
    `/api/v1/institutions/${institutionId}/submissions/receipt?${params.toString()}`
  );
}
