export interface ChangeRequestStudentInfo {
  id: number;
  apaar_id: string;
  name: string;
  course_id: number | null;
  course_name: string | null;
  academic_year: string;
  status: string;
  is_locked: boolean;
}

export interface ChangeRequestInstitutionInfo {
  id: number;
  aicte_id: string;
  name: string;
  state: string;
}

export type ChangeRequestStatus = 'pending' | 'approved' | 'rejected';

export interface ChangeRequest {
  id: number;
  student_id: number;
  student: ChangeRequestStudentInfo | null;
  institution_id: number;
  institution: ChangeRequestInstitutionInfo | null;
  field: string;
  old_value: string | null;
  new_value: string;
  reason: string;
  status: ChangeRequestStatus;
  decided_by: number | null;
  decided_by_email: string | null;
  decided_at: string | null;
  document_ref: string | null;
  decision_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChangeRequestListResponse {
  items: ChangeRequest[];
  total: number;
  limit: number;
  offset: number;
}

export interface ChangeRequestCreatePayload {
  student_id: number;
  field: string;
  new_value: string;
  reason: string;
  document?: File | null;
  document_ref?: string | null;
}

export interface ChangeRequestDecisionPayload {
  decision: 'approve' | 'reject';
  decision_note?: string | null;
}
