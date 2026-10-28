import { api, getStoredToken } from "./client";
import type {
  ReportFilterState,
  ReportFormat,
  ReportPreviewResponse,
  ReportType,
} from "../types/reports";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) || "";

/**
 * Fetch structured preview data for rendering in frontend table before download.
 */
export async function fetchReportPreview(
  reportType: ReportType,
  filters: ReportFilterState
): Promise<ReportPreviewResponse> {
  const query = new URLSearchParams();
  query.set("report_type", reportType);
  if (filters.academic_year) query.set("academic_year", filters.academic_year);
  if (filters.state) query.set("state", filters.state);
  if (filters.course) query.set("course", filters.course);
  if (filters.institution_id) query.set("institution_id", String(filters.institution_id));
  if (filters.course_id) query.set("course_id", String(filters.course_id));
  if (filters.base_year) query.set("base_year", filters.base_year);
  if (filters.target_year) query.set("target_year", filters.target_year);

  return api.get<ReportPreviewResponse>(`/api/v1/reports/preview?${query.toString()}`);
}

/**
 * Trigger browser file download with authenticated Bearer token.
 */
export async function downloadReportFile(
  reportType: ReportType,
  format: ReportFormat,
  filters: ReportFilterState
): Promise<void> {
  const query = new URLSearchParams();
  query.set("format", format);
  if (filters.academic_year) query.set("academic_year", filters.academic_year);
  if (filters.state) query.set("state", filters.state);
  if (filters.course) query.set("course", filters.course);
  if (filters.institution_id) query.set("institution_id", String(filters.institution_id));
  if (filters.course_id) query.set("course_id", String(filters.course_id));
  if (filters.base_year) query.set("base_year", filters.base_year);
  if (filters.target_year) query.set("target_year", filters.target_year);

  const endpoint = `/api/v1/reports/${reportType}?${query.toString()}`;
  await executeBlobDownload(endpoint, `${reportType}.${format}`);
}

/**
 * Convenience helper for colleges to download their own submission report.
 */
export async function downloadCollegeSubmission(
  institutionId: number,
  format: ReportFormat,
  academicYear: string = "2026-27"
): Promise<void> {
  const endpoint = `/api/v1/institutions/${institutionId}/reports/submission?format=${format}&academic_year=${academicYear}`;
  await executeBlobDownload(endpoint, `submission_report_${institutionId}_${academicYear}.${format}`);
}

/**
 * Convenience helper for colleges to download their own accreditation snapshot.
 */
export async function downloadCollegeAccreditation(
  institutionId: number,
  format: ReportFormat,
  academicYear: string = "2026-27"
): Promise<void> {
  const endpoint = `/api/v1/institutions/${institutionId}/reports/accreditation?format=${format}&academic_year=${academicYear}`;
  await executeBlobDownload(endpoint, `accreditation_snapshot_${institutionId}_${academicYear}.${format}`);
}

/**
 * Internal helper to download a blob from an authenticated endpoint.
 */
async function executeBlobDownload(endpoint: string, fallbackFilename: string): Promise<void> {
  const token = getStoredToken();
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    method: "GET",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!response.ok) {
    let errMsg = `Failed to download report (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) errMsg = errJson.detail;
    } catch {
      // not JSON
    }
    throw new Error(errMsg);
  }

  // Extract filename from Content-Disposition if present
  let filename = fallbackFilename;
  const disposition = response.headers.get("content-disposition");
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
}
