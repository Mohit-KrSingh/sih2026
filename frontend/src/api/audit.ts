import { api } from "./client";
import type {
  AuditChainVerificationResponse,
  AuditLogFilters,
  AuditLogListResponse,
} from "../types/audit";

/**
 * Fetch paginated audit log entries with filters.
 */
export async function getAuditLogs(filters?: AuditLogFilters): Promise<AuditLogListResponse> {
  const qs = new URLSearchParams();
  if (filters?.action) qs.append("action", filters.action);
  if (filters?.actor_id) qs.append("actor_id", filters.actor_id);
  if (filters?.actor_role) qs.append("actor_role", filters.actor_role);
  if (filters?.entity) qs.append("entity", filters.entity);
  if (filters?.entity_id) qs.append("entity_id", filters.entity_id);
  if (filters?.from_date) qs.append("from_date", filters.from_date);
  if (filters?.to_date) qs.append("to_date", filters.to_date);
  if (filters?.limit) qs.append("limit", String(filters.limit));
  if (filters?.offset) qs.append("offset", String(filters.offset));

  const query = qs.toString() ? `?${qs.toString()}` : "";
  return api.get<AuditLogListResponse>(`/api/v1/audit${query}`);
}

/**
 * Cryptographically verify complete SHA-256 hash chain integrity.
 */
export async function verifyAuditChain(): Promise<AuditChainVerificationResponse> {
  return api.get<AuditChainVerificationResponse>("/api/v1/audit/verify-chain");
}
