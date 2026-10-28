/**
 * API client for DPDP privacy policy and data minimisation specifications.
 * Spec: Section 2, 16 & TASKS.md T38
 */

import { api } from "./client";

export interface FieldMetadata {
  field: string;
  group: string;
  description: string;
  storage: string;
}

export interface ProhibitedField {
  field: string;
  reason: string;
}

export interface DataMinimisationSpec {
  collected_fields: FieldMetadata[];
  prohibited_fields: ProhibitedField[];
}

export interface DataFiduciaryInfo {
  name: string;
  ministry: string;
  statutory_mandate: string;
}

export interface CryptographicSafeguards {
  dob_encryption: string;
  apaar_log_redaction: string;
  audit_trail: string;
  verifiable_credentials: string;
}

export interface ConsentFrameworkSpec {
  statutory_ttl_hours: number;
  single_use_enforced: boolean;
  student_revocation_right: boolean;
  minimal_disclosure_fields: string[];
  restricted_from_verifiers: string[];
}

export interface DataRetentionPolicy {
  student_enrolment_records: string;
  consent_requests: string;
  audit_log: string;
}

export interface GrievanceRedressalInfo {
  officer: string;
  designation: string;
  email: string;
  address: string;
  resolution_sla: string;
}

export interface PrivacyPolicyResponse {
  status: string;
  framework: string;
  effective_date: string;
  data_fiduciary: DataFiduciaryInfo;
  purpose_limitation: string[];
  data_minimisation: DataMinimisationSpec;
  cryptographic_safeguards: CryptographicSafeguards;
  consent_framework: ConsentFrameworkSpec;
  data_principal_rights: string[];
  data_retention: DataRetentionPolicy;
  grievance_redressal: GrievanceRedressalInfo;
}

export const FALLBACK_PRIVACY_DATA: PrivacyPolicyResponse = {
  status: "compliant",
  framework: "Digital Personal Data Protection Act (DPDP), 2023",
  effective_date: "2026-01-01",
  data_fiduciary: {
    name: "All India Council for Technical Education (AICTE)",
    ministry: "Ministry of Education, Government of India",
    statutory_mandate: "AICTE Act 1987 & National Technical Education Regulations",
  },
  purpose_limitation: [
    "Academic enrolment record management keyed by APAAR ID",
    "Reconciliation of institutional intake quotas and supernumerary caps",
    "Automated detection and prevention of concurrent cross-college duplicate enrolments",
    "Live regulatory compliance monitoring and anomaly alerts for AICTE officers",
    "Consent-gated verifiable academic credential issuance for authorised verifiers",
  ],
  data_minimisation: {
    collected_fields: [
      { field: "apaar_id", group: "Identity", description: "12-digit national academic identifier", storage: "Plaintext indexed" },
      { field: "name", group: "Identity", description: "Student full name", storage: "Plaintext" },
      { field: "dob", group: "Identity", description: "Date of birth", storage: "Encrypted at rest (Fernet AES-128-CBC + HMAC-SHA256)" },
      { field: "gender", group: "Identity", description: "Gender (Male, Female, Other)", storage: "Plaintext" },
      { field: "course", group: "Admission", description: "Approved academic course/program", storage: "Plaintext foreign key" },
      { field: "branch", group: "Admission", description: "Approved technical engineering/technology branch", storage: "Plaintext" },
      { field: "admission_year", group: "Admission", description: "Academic year of admission (e.g. 2026-27)", storage: "Plaintext indexed" },
      { field: "enrolment_no", group: "Admission", description: "College's own internal student roll/enrolment ID", storage: "Plaintext unique within course" },
      { field: "admission_date", group: "Admission", description: "Calendar date of official admission", storage: "ISO date" },
      { field: "admission_mode", group: "Admission", description: "Admission channel (JEE Main, State, Management, etc.)", storage: "Enum string" },
      { field: "seat_type", group: "Admission", description: "Seat allocation type (Regular or Supernumerary)", storage: "Enum string" },
      { field: "reservation_category", group: "Category", description: "Statutory reservation category (General, OBC, SC, ST, EWS)", storage: "Enum string" },
      { field: "nri", group: "Category", description: "Non-Resident Indian status (Yes or No)", storage: "Flag string" },
      { field: "oci", group: "Category", description: "Overseas Citizen of India status (Yes or No)", storage: "Flag string" },
      { field: "foreign_national", group: "Category", description: "Foreign national status (Yes or No)", storage: "Flag string" },
      { field: "country", group: "Category", description: "Country of citizenship (only for foreign nationals)", storage: "String or null" },
    ],
    prohibited_fields: [
      { field: "Aadhaar / National Identity Numbers", reason: "Hard Rule 2: APAAR ID is the sole statutory student identifier; Aadhaar is strictly prohibited." },
      { field: "Parents / Guardians Personal Information", reason: "Non-essential for higher educational enrollment verification or seat quota tracking." },
      { field: "Residential Address & Geolocation Data", reason: "Excluded under DPDP data minimisation; not required for regulatory oversight." },
      { field: "Photographs & Biometric Signatures", reason: "No facial recognition or biometric data is collected or processed." },
      { field: "Family Income & Financial Statements", reason: "Financial background is outside the scope of central academic quota tracking." },
      { field: "Examination Marks & Academic Transcripts", reason: "Maintained by individual institutional ERPs; only enrollment status is tracked." },
    ],
  },
  cryptographic_safeguards: {
    dob_encryption: "Fernet 128-bit AES in CBC mode with PKCS7 padding and HMAC-SHA256 authentication",
    apaar_log_redaction: "Automated regex masking in all runtime logs (redacted to ********<last4>)",
    audit_trail: "Tamper-evident append-only hash chaining with SHA-256 (hash = SHA256(prev_hash + canonical_row))",
    verifiable_credentials: "High-assurance Ed25519 digital signatures over canonical JSON tuples",
  },
  consent_framework: {
    statutory_ttl_hours: 24,
    single_use_enforced: true,
    student_revocation_right: true,
    minimal_disclosure_fields: ["institution", "course", "years", "status", "verification_id", "verified_by"],
    restricted_from_verifiers: ["dob", "reservation_category", "nri_oci_status", "contact_information"],
  },
  data_principal_rights: [
    "Right to Access: Students can view all institutions holding enrolment records under their APAAR ID.",
    "Right to Consent Management: Students may review, approve, or deny all employer verification requests.",
    "Right to Consent History: Complete audit trail of historical verification requests and outcomes.",
    "Right to Grievance Redressal: Direct statutory grievance mechanism with the AICTE Data Protection Officer.",
  ],
  data_retention: {
    student_enrolment_records: "Retained for the duration of the student's academic degree tenure plus statutory regulatory audit period.",
    consent_requests: "24 hours active validity; decision audit trail permanently retained in append-only log.",
    audit_log: "Permanent tamper-evident cryptographic log for regulatory non-repudiation and accountability.",
  },
  grievance_redressal: {
    officer: "Data Protection Officer (DPO), AICTE Central Repository",
    designation: "Director (Legal Compliance & Data Protection)",
    email: "dpo@aicte-india.org",
    address: "All India Council for Technical Education, Nelson Mandela Marg, Vasant Kunj, New Delhi - 110070, India",
    resolution_sla: "30 days statutory response window",
  },
};

export async function getPrivacyPolicy(): Promise<PrivacyPolicyResponse> {
  try {
    return await api.get<PrivacyPolicyResponse>("/api/v1/privacy");
  } catch {
    return FALLBACK_PRIVACY_DATA;
  }
}
