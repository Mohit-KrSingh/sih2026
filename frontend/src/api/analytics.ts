import { api } from "./client";
import type {
  AnomalyScoreListResponse,
  ComplianceListResponse,
  CourseMetricsItem,
  DrilldownResponse,
  DuplicateListResponse,
  NoticeResponse,
  OverviewMetrics,
  ResolveFlagRequest,
  ResolveFlagResponse,
  SendNoticeRequest,
  SSEEventPayload,
  StateMetricsItem,
  SubmissionProgressCounts,
} from "../types/analytics";

/**
 * Fetch high-level oversight metrics for AICTE dashboard.
 */
export async function getOverviewMetrics(academicYear = "2026-27"): Promise<OverviewMetrics> {
  return api.get<OverviewMetrics>(`/api/v1/analytics/overview?academic_year=${encodeURIComponent(academicYear)}`);
}

/**
 * Fetch metrics aggregated by state.
 */
export async function getStateMetrics(academicYear = "2026-27"): Promise<{ academic_year: string; total_states: number; items: StateMetricsItem[] }> {
  return api.get(`/api/v1/analytics/by-state?academic_year=${encodeURIComponent(academicYear)}`);
}

/**
 * Fetch metrics aggregated by course discipline.
 */
export async function getCourseMetrics(
  academicYear = "2026-27",
  level?: string
): Promise<{ academic_year: string; total_disciplines: number; items: CourseMetricsItem[] }> {
  const qs = new URLSearchParams({ academic_year: academicYear });
  if (level) qs.append("level", level);
  return api.get(`/api/v1/analytics/by-course?${qs.toString()}`);
}

/**
 * Fetch annual submission progress across all colleges.
 */
export async function getSubmissionProgress(params?: {
  academic_year?: string;
  state?: string;
  status?: string;
}): Promise<{
  academic_year: string;
  total_colleges: number;
  counts_by_status: SubmissionProgressCounts;
  colleges: any[];
}> {
  const qs = new URLSearchParams();
  if (params?.academic_year) qs.append("academic_year", params.academic_year);
  if (params?.state) qs.append("state", params.state);
  if (params?.status) qs.append("status", params.status);
  return api.get(`/api/v1/analytics/submission-progress?${qs.toString()}`);
}

/**
 * Fetch over-intake compliance list & red list colleges.
 */
export async function getComplianceList(params?: {
  academic_year?: string;
  state?: string;
  min_overshoot?: number;
}): Promise<ComplianceListResponse> {
  const qs = new URLSearchParams();
  if (params?.academic_year) qs.append("academic_year", params.academic_year);
  if (params?.state) qs.append("state", params.state);
  if (params?.min_overshoot !== undefined) qs.append("min_overshoot", String(params.min_overshoot));
  return api.get<ComplianceListResponse>(`/api/v1/analytics/compliance?${qs.toString()}`);
}

/**
 * Hierarchical drill-down: State -> College -> Course -> Flagged Students.
 */
export async function getDrilldown(params?: {
  academic_year?: string;
  state?: string;
  institution_id?: number;
  course_id?: number;
}): Promise<DrilldownResponse> {
  const qs = new URLSearchParams();
  if (params?.academic_year) qs.append("academic_year", params.academic_year);
  if (params?.state) qs.append("state", params.state);
  if (params?.institution_id) qs.append("institution_id", String(params.institution_id));
  if (params?.course_id) qs.append("course_id", String(params.course_id));
  return api.get<DrilldownResponse>(`/api/v1/analytics/drilldown?${qs.toString()}`);
}

/**
 * Fetch cross-college duplicate enrolments.
 */
export async function getDuplicates(params?: {
  academic_year?: string;
  rule_code?: string;
  status?: string;
}): Promise<DuplicateListResponse> {
  const qs = new URLSearchParams();
  if (params?.academic_year) qs.append("academic_year", params.academic_year);
  if (params?.rule_code) qs.append("rule_code", params.rule_code);
  if (params?.status) qs.append("status", params.status);
  return api.get<DuplicateListResponse>(`/api/v1/analytics/duplicates?${qs.toString()}`);
}

/**
 * Fetch ML and statistical anomaly scores.
 */
export async function getAnomalies(params?: {
  academic_year?: string;
  flagged_only?: boolean;
  institution_id?: number;
  scan_now?: boolean;
}): Promise<AnomalyScoreListResponse> {
  const qs = new URLSearchParams();
  if (params?.academic_year) qs.append("academic_year", params.academic_year);
  if (params?.flagged_only !== undefined) qs.append("flagged_only", String(params.flagged_only));
  if (params?.institution_id) qs.append("institution_id", String(params.institution_id));
  if (params?.scan_now !== undefined) qs.append("scan_now", String(params.scan_now));
  return api.get<AnomalyScoreListResponse>(`/api/v1/analytics/anomalies?${qs.toString()}`);
}

/**
 * Action Tool: Send compliance notice to an institution.
 */
export async function sendNotice(payload: SendNoticeRequest): Promise<NoticeResponse> {
  return api.post<NoticeResponse>("/api/v1/analytics/action/notice", payload);
}

/**
 * Action Tool: Mark a validation flag as resolved or dismissed.
 */
export async function resolveFlag(payload: ResolveFlagRequest): Promise<ResolveFlagResponse> {
  return api.post<ResolveFlagResponse>("/api/v1/analytics/action/resolve-flag", payload);
}

/**
 * Get recent system events from memory buffer.
 */
export async function getRecentEvents(params?: {
  limit?: number;
  event_type?: string;
}): Promise<SSEEventPayload[]> {
  const qs = new URLSearchParams();
  if (params?.limit) qs.append("limit", String(params.limit));
  if (params?.event_type) qs.append("event_type", params.event_type);
  return api.get<SSEEventPayload[]>(`/api/v1/analytics/events?${qs.toString()}`);
}

/**
 * Subscribe to live Server-Sent Events (SSE).
 * Returns cleanup unsubscribe function.
 */
export function subscribeLiveEvents(
  onEvent: (event: SSEEventPayload) => void,
  onError?: (err: any) => void
): () => void {
  const token = localStorage.getItem("apaar_access_token");
  let eventSource: EventSource | null = null;
  let pollingInterval: any = null;

  // Attempt EventSource connection if available in environment
  if (typeof EventSource !== "undefined") {
    try {
      // EventSource with query parameter token or cookie
      const streamUrl = `/api/v1/analytics/stream${token ? `?token=${encodeURIComponent(token)}` : ""}`;
      eventSource = new EventSource(streamUrl);

      eventSource.onmessage = (e) => {
        try {
          const payload = JSON.parse(e.data);
          onEvent({
            id: payload.id || String(Date.now()),
            event: payload.event || "message",
            data: payload.data || payload,
            timestamp: payload.timestamp || new Date().toISOString(),
          });
        } catch {
          // ignore parse error
        }
      };

      // Also listen to named event types
      const knownEvents = [
        "submission_created",
        "submission_promoted",
        "flag_detected",
        "duplicate_enrolment",
        "anomaly_detected",
        "notice_sent",
        "flag_resolved",
        "heartbeat",
      ];

      knownEvents.forEach((evtName) => {
        eventSource?.addEventListener(evtName, (e: any) => {
          try {
            const parsed = JSON.parse(e.data);
            onEvent({
              id: parsed.id || String(Date.now()),
              event: evtName,
              data: parsed.data || parsed,
              timestamp: parsed.timestamp || new Date().toISOString(),
            });
          } catch {
            // ignore
          }
        });
      });

      eventSource.onerror = (err) => {
        if (onError) onError(err);
      };
    } catch (e) {
      if (onError) onError(e);
    }
  }

  // Backup fallback: Poll recent events every 6 seconds to ensure reliable real-time updates
  pollingInterval = setInterval(async () => {
    try {
      const events = await getRecentEvents({ limit: 5 });
      if (events && events.length > 0) {
        events.forEach((ev) => onEvent(ev));
      }
    } catch {
      // silent fail in polling fallback
    }
  }, 6000);

  return () => {
    if (eventSource) {
      eventSource.close();
    }
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
  };
}
