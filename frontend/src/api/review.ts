/**
 * API client functions for AICTE Review Queue and College Clarification Queries.
 * SPEC.md Section 10 & 12, TASKS.md T25.
 */

import { apiClient, getStoredToken } from "./client";
import type {
  CollegeQueryListResponse,
  CollegeQueryResponse,
  ReviewDecisionRequest,
  ReviewItemDetailResponse,
  ReviewItemListResponse,
} from "../types/review";

export async function fetchReviewItems(params?: {
  status?: string;
  academic_year?: string;
  institution_id?: number;
  search?: string;
}): Promise<ReviewItemListResponse> {
  const query = new URLSearchParams();
  if (params?.status && params.status !== "all") query.set("status", params.status);
  if (params?.academic_year) query.set("academic_year", params.academic_year);
  if (params?.institution_id) query.set("institution_id", String(params.institution_id));
  if (params?.search) query.set("search", params.search);

  const qs = query.toString() ? `?${query.toString()}` : "";
  return apiClient<ReviewItemListResponse>(`/api/v1/review/items${qs}`);
}

export async function fetchReviewItemDetail(itemId: number): Promise<ReviewItemDetailResponse> {
  return apiClient<ReviewItemDetailResponse>(`/api/v1/review/items/${itemId}`);
}

export async function submitReviewDecision(
  itemId: number,
  payload: ReviewDecisionRequest,
): Promise<ReviewItemDetailResponse> {
  return apiClient<ReviewItemDetailResponse>(`/api/v1/review/items/${itemId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getReviewDocumentDownloadUrl(itemId: number, justificationId: number): string {
  const apiBase = (import.meta.env.VITE_API_BASE_URL as string) || "";
  return `${apiBase}/api/v1/review/items/${itemId}/documents/${justificationId}`;
}

export async function fetchCollegeQueries(
  institutionId: number,
  params?: {
    state?: string;
    academic_year?: string;
  },
): Promise<CollegeQueryListResponse> {
  const query = new URLSearchParams();
  if (params?.state && params.state !== "all") query.set("state", params.state);
  if (params?.academic_year) query.set("academic_year", params.academic_year);

  const qs = query.toString() ? `?${query.toString()}` : "";
  return apiClient<CollegeQueryListResponse>(`/api/v1/institutions/${institutionId}/queries${qs}`);
}

export async function fetchCollegeQueryDetail(
  institutionId: number,
  queryId: number,
): Promise<CollegeQueryResponse> {
  return apiClient<CollegeQueryResponse>(`/api/v1/institutions/${institutionId}/queries/${queryId}`);
}

export async function respondToCollegeQuery(
  institutionId: number,
  queryId: number,
  payload: {
    response: string;
    document?: File;
  },
): Promise<CollegeQueryResponse> {
  const token = getStoredToken();
  const apiBase = (import.meta.env.VITE_API_BASE_URL as string) || "";

  const formData = new FormData();
  formData.append("response", payload.response);
  if (payload.document) {
    formData.append("document", payload.document);
  }

  const res = await fetch(`${apiBase}/api/v1/institutions/${institutionId}/queries/${queryId}/respond`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to submit response." }));
    throw new Error(err.detail || "Failed to submit response.");
  }

  return res.json();
}
