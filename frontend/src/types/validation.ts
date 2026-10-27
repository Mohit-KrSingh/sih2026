export type FlagLevel = "error" | "exception" | "warning" | "info";

export interface ValidationFlag {
  id?: number;
  rule_code: string;
  level: FlagLevel;
  message: string;
  field_name?: string | null;
  row_number?: number | null;
  fix_hint?: string | null;
  status?: string;
  justification?: string | null;
}
