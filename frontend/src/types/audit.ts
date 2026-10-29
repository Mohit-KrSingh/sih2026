/**
 * Types for Hash-Chained Audit Trail.
 * Spec: Section 15 & TASKS.md T06, T29
 */

export interface AuditLogItem {
  id: number;
  ts: string;
  actor_id: string | null;
  actor_role: string | null;
  action: string;
  entity: string;
  entity_id: string | null;
  before_json: Record<string, any> | null;
  after_json: Record<string, any> | null;
  ip: string | null;
  prev_hash: string | null;
  hash: string;
}

export interface AuditLogListResponse {
  total: number;
  items: AuditLogItem[];
  limit: number;
  offset: number;
}

export interface AuditChainVerificationResponse {
  verified: boolean;
  total_records: number;
  first_broken_id: number | null;
  broken_index: number | null;
  reason: string | null;
}

export interface AuditLogFilters {
  action?: string;
  actor_id?: string;
  actor_role?: string;
  entity?: string;
  entity_id?: string;
  from_date?: string;
  to_date?: string;
  limit?: number;
  offset?: number;
}
