import { apiClient } from "./client";

export interface ApiKeyItem {
  id: number;
  institution_id: number;
  name: string;
  key_prefix: string;
  scopes: string[];
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
  is_active: boolean;
}

export interface ApiKeyCreatedResponse extends ApiKeyItem {
  raw_key: string;
}

export interface ApiKeyRotateResponse {
  id: number;
  institution_id: number;
  name: string;
  key_prefix: string;
  raw_key: string;
  scopes: string[];
  updated_at: string;
}

export interface ApiKeyListResponse {
  items: ApiKeyItem[];
  total: number;
}

export interface CreateApiKeyRequest {
  name: string;
  scopes: string[];
}

export async function listApiKeys(institutionId: number): Promise<ApiKeyListResponse> {
  return apiClient<ApiKeyListResponse>(`/api/v1/institutions/${institutionId}/api-keys`);
}

export async function createApiKey(
  institutionId: number,
  payload: CreateApiKeyRequest
): Promise<ApiKeyCreatedResponse> {
  return apiClient<ApiKeyCreatedResponse>(`/api/v1/institutions/${institutionId}/api-keys`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function rotateApiKey(
  institutionId: number,
  keyId: number
): Promise<ApiKeyRotateResponse> {
  return apiClient<ApiKeyRotateResponse>(
    `/api/v1/institutions/${institutionId}/api-keys/${keyId}/rotate`,
    {
      method: "POST",
    }
  );
}

export async function revokeApiKey(
  institutionId: number,
  keyId: number
): Promise<ApiKeyItem> {
  return apiClient<ApiKeyItem>(
    `/api/v1/institutions/${institutionId}/api-keys/${keyId}/revoke`,
    {
      method: "POST",
    }
  );
}
