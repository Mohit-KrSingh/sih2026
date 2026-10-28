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
