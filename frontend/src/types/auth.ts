export type Role =
  | "aicte_admin"
  | "aicte_officer"
  | "college_admin"
  | "college_staff"
  | "college_viewer"
  | "verifier";

export interface User {
  id: number;
  email: string;
  role: Role;
  institution_id?: number | null;
  is_active: boolean;
  last_login?: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
  mfa_required?: boolean;
  mfa_token?: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
  mfa_code?: string;
}

export interface MfaVerifyPayload {
  mfa_token: string;
  code: string;
}

export interface ApiErrorDetail {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
}

export interface ApiErrorResponse {
  detail?: string | ApiErrorDetail[];
}
