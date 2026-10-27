/**
 * Types for Validation Rule Configuration.
 * Spec: Section 9.2, 9.3, 12 & TASKS.md T29
 */

export interface RuleConfigItem {
  rule_code: string;
  scope: "file" | "row" | "course" | "cross" | "anomaly" | string;
  default_level: "error" | "exception" | "warning" | "info" | string;
  current_level: "error" | "exception" | "warning" | "info" | string;
  meaning: string;
  default_params: Record<string, any>;
  current_params: Record<string, any>;
  enabled: boolean;
  is_overridden: boolean;
  updated_by: number | null;
  updated_at: string | null;
}

export interface RuleListResponse {
  total: number;
  overridden_count: number;
  items: RuleConfigItem[];
}

export interface RuleConfigUpdateRequest {
  level?: "error" | "exception" | "warning" | "info";
  params?: Record<string, any>;
  enabled?: boolean;
}
