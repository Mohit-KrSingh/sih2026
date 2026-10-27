import { api, clearStoredTokens, setStoredTokens } from "./client";
import type { LoginCredentials, MfaVerifyPayload, TokenResponse, User } from "../types/auth";

export async function loginApi(credentials: LoginCredentials): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>("/api/v1/auth/login", {
    email: credentials.email.trim(),
    password: credentials.password,
    mfa_code: credentials.mfa_code ? credentials.mfa_code.trim() : undefined,
  });

  if (!response.mfa_required && response.access_token) {
    setStoredTokens(response.access_token, response.refresh_token);
  }

  return response;
}

export async function verifyMfaApi(payload: MfaVerifyPayload): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>("/api/v1/auth/mfa/verify", {
    mfa_token: payload.mfa_token,
    code: payload.code.trim(),
  });

  if (response.access_token) {
    setStoredTokens(response.access_token, response.refresh_token);
  }

  return response;
}

export async function refreshTokenApi(refreshToken: string): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>("/api/v1/auth/refresh", {
    refresh_token: refreshToken,
  });

  if (response.access_token) {
    setStoredTokens(response.access_token, response.refresh_token);
  }

  return response;
}

export async function getMeApi(): Promise<User> {
  return api.get<User>("/api/v1/auth/me");
}

export function logoutApi(): void {
  clearStoredTokens();
}
