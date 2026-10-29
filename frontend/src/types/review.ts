/**
 * TypeScript types for AICTE Review Queue and College Clarification Queries.
 * SPEC.md Section 10 & 12, TASKS.md T25.
 */

import type { FlagLevel } from "./validation";
import type { SubmissionStatus } from "./submissions";

export type ReviewStatus =
  | "pending"
  | "under_review"
  | "accepted"
  | "query_raised"
  | "escalated";

export type ReviewDecision = "accept" | "query" | "escalate";

export type QueryState = "pending" | "answered" | "closed";

export interface ReviewJustificationDetail {
  id: number;
  flag_id: number;
  text: string;
  document_ref?: string | null;
  document_filename?: string | null;
  by_user_id?: number | null;
  by_user_email?: string | null;
  at: string;
}

export interface ReviewFlagDetail {
  id: number;
  submission_id: number;
  rule_code: string;
  level: FlagLevel;
  field?: string | null;
  row_ref?: string | null;
  message: string;
  fix_hint?: string | null;
  status: string;
  student_id?: number | null;
  student_name?: string | null;
  student_apaar?: string | null;
  course_id?: number | null;
  course_name?: string | null;
  branch?: string | null;
  justifications: ReviewJustificationDetail[];
}

export interface QueryItemResponse {
  id: number;
  review_item_id?: number | null;
  submission_id: number;
  message: string;
  response?: string | null;
  state: QueryState;
  created_by?: number | null;
  created_by_email?: string | null;
  responded_by?: number | null;
  responded_by_email?: string | null;
  created_at: string;
  responded_at?: string | null;
}

export interface ReviewItemSummary {
  id: number;
  submission_id: number;
  institution_id: number;
  institution_name: string;
  aicte_id: string;
  state: string;
  academic_year: string;
  receipt_no?: string | null;
  status: ReviewStatus;
  decision?: string | null;
  decision_note?: string | null;
  decided_at?: string | null;
  assigned_to?: number | null;
  assigned_to_email?: string | null;
  flag_ids: number[];
  rule_codes: string[];
  flag_count: number;
  pending_queries_count: number;
  created_at: string;
  updated_at: string;
}

export interface ReviewItemListResponse {
  total: number;
  pending_count: number;
  under_review_count: number;
  queries_raised_count: number;
  escalated_count: number;
  accepted_count: number;
  items: ReviewItemSummary[];
}

export interface ReviewItemDetailResponse {
  id: number;
  submission_id: number;
  institution_id: number;
  institution_name: string;
  aicte_id: string;
  state: string;
  district?: string | null;
  academic_year: string;
  submission_status: SubmissionStatus;
  receipt_no?: string | null;
  submitted_at?: string | null;
  status: ReviewStatus;
  decision?: string | null;
  decision_note?: string | null;
  decided_at?: string | null;
  assigned_to?: number | null;
  assigned_to_email?: string | null;
  flags: ReviewFlagDetail[];
  queries: QueryItemResponse[];
  created_at: string;
  updated_at: string;
}

export interface ReviewDecisionRequest {
  decision: ReviewDecision;
  note: string;
}

export interface CollegeQueryResponse {
  id: number;
  review_item_id?: number | null;
  submission_id: number;
  institution_id: number;
  institution_name: string;
  academic_year: string;
  receipt_no?: string | null;
  message: string;
  response?: string | null;
  state: QueryState;
  created_at: string;
  responded_at?: string | null;
  officer_name?: string | null;
  flags: ReviewFlagDetail[];
}

export interface CollegeQueryListResponse {
  total: number;
  pending_count: number;
  items: CollegeQueryResponse[];
}

export interface CollegeQueryRespondRequest {
  response: string;
  document_ref?: string | null;
}
