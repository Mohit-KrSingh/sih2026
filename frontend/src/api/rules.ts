import { api } from "./client";
import type {
  RuleConfigItem,
  RuleConfigUpdateRequest,
  RuleListResponse,
} from "../types/rules";

/**
 * Fetch all catalogued validation rules and active configurations.
 */
export async function getRules(): Promise<RuleListResponse> {
  return api.get<RuleListResponse>("/api/v1/rules");
}

/**
 * Fetch configuration of a specific rule.
 */
export async function getRule(ruleCode: string): Promise<RuleConfigItem> {
  return api.get<RuleConfigItem>(`/api/v1/rules/${encodeURIComponent(ruleCode)}`);
}

/**
 * Update rule configuration (level, parameters, enabled).
 */
export async function updateRuleConfig(
  ruleCode: string,
  payload: RuleConfigUpdateRequest
): Promise<RuleConfigItem> {
  return api.put<RuleConfigItem>(`/api/v1/rules/${encodeURIComponent(ruleCode)}`, payload);
}

/**
 * Reset rule configuration back to catalogue defaults.
 */
export async function resetRuleConfig(ruleCode: string): Promise<RuleConfigItem> {
  return api.post<RuleConfigItem>(`/api/v1/rules/${encodeURIComponent(ruleCode)}/reset`, {});
}
