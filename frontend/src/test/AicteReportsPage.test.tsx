import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import * as reportsApi from "../api/reports";
import * as institutionsApi from "../api/institutions";
import { AicteReportsPage } from "../pages/AicteReportsPage";
import type { ReportPreviewResponse } from "../types/reports";

const mockPreviewData: ReportPreviewResponse = {
  report_type: "enrolment-by-state-course",
  title: "Enrolment by State and Course Report",
  subtitle: "National intake, admissions, and capacity fill rate",
  academic_year: "2026-27",
  generated_at: "2026-10-28 02:30:00 UTC",
  filters_applied: { academic_year: "2026-27" },
  summary_boxes: [
    { label: "Approved Intake", value: 3600, detail: "Sanctioned quota" },
    { label: "Total Enrolled", value: 3100, detail: "Active students" },
    { label: "Overall Fill Rate", value: "86.1%", detail: "Capacity utilization" },
  ],
  columns: [
    "State",
    "Course Discipline",
    "Level",
    "Institutions Offering",
    "Approved Intake",
    "Total Admitted",
    "Fill Rate (%)",
  ],
  rows: [
    ["Maharashtra", "Computer Science", "UG", 10, 1200, 1150, 95.8],
    ["Karnataka", "Information Technology", "UG", 8, 960, 890, 92.7],
  ],
  totals_row: ["National Total", "-", "-", 18, 2160, 2040, 94.4],
  total_records: 2,
  notes: ["Admissions exclude withdrawn and transferred students."],
};

describe("AicteReportsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(institutionsApi, "listInstitutions").mockResolvedValue({
      total: 2,
      items: [
        {
          id: 1,
          aicte_id: "1-10000001",
          name: "Pune Engineering Institute",
          state: "Maharashtra",
          district: "Pune",
          address: "Pune",
          official_email: "pune@edu.in",
          official_phone: "+911234567890",
          head_name: "Dr. Pune",
          affiliating_university: "SPPU",
          approval_status: "active",
          account_status: "active",
        },
      ],
    } as any);

    vi.spyOn(reportsApi, "fetchReportPreview").mockResolvedValue(mockPreviewData);
    vi.spyOn(reportsApi, "downloadReportFile").mockResolvedValue();
  });

  it("renders page header, catalog list, and preview table", async () => {
    render(
      <BrowserRouter>
        <AicteReportsPage />
      </BrowserRouter>
    );

    expect(screen.getByText("National Reports & Data Exports")).toBeInTheDocument();

    // Check report items exist in the catalog
    expect(screen.getAllByText("Enrolment by State and Course").length).toBeGreaterThan(0);
    expect(screen.getByText("Seat Utilisation & Quota Compliance")).toBeInTheDocument();
    expect(screen.getByText("Colleges with Exceptions Register")).toBeInTheDocument();
    expect(screen.getByText("Cross-College Duplicate Enrolments")).toBeInTheDocument();
    expect(screen.getByText("Year-over-Year (YoY) Admission Trends")).toBeInTheDocument();
    expect(screen.getByText("Accreditation Compliance Snapshot")).toBeInTheDocument();
    expect(screen.getByText("College Student Submission Register")).toBeInTheDocument();

    // Wait for preview to load
    await waitFor(() => {
      expect(screen.getAllByText("Approved Intake").length).toBeGreaterThan(0);
      expect(screen.getByText("3600")).toBeInTheDocument();
      expect(screen.getAllByText("Maharashtra").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Karnataka").length).toBeGreaterThan(0);
      expect(screen.getByText("National Total")).toBeInTheDocument();
    });
  });

  it("switches report type when catalog item is clicked", async () => {
    render(
      <BrowserRouter>
        <AicteReportsPage />
      </BrowserRouter>
    );

    const dupReportBtn = screen.getByText("Cross-College Duplicate Enrolments");
    fireEvent.click(dupReportBtn);

    await waitFor(() => {
      expect(reportsApi.fetchReportPreview).toHaveBeenCalledWith(
        "duplicate-enrolments",
        expect.anything()
      );
    });
  });

  it("triggers CSV, XLSX, and PDF downloads on click", async () => {
    render(
      <BrowserRouter>
        <AicteReportsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText("Approved Intake").length).toBeGreaterThan(0);
    });

    const csvBtn = screen.getByRole("button", { name: /^CSV$/i });
    fireEvent.click(csvBtn);
    expect(reportsApi.downloadReportFile).toHaveBeenCalledWith(
      "enrolment-by-state-course",
      "csv",
      expect.anything()
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Excel \(XLSX\)/i })).not.toBeDisabled();
    });

    const xlsxBtn = screen.getByRole("button", { name: /Excel \(XLSX\)/i });
    fireEvent.click(xlsxBtn);
    expect(reportsApi.downloadReportFile).toHaveBeenCalledWith(
      "enrolment-by-state-course",
      "xlsx",
      expect.anything()
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /PDF Report/i })).not.toBeDisabled();
    });

    const pdfBtn = screen.getByRole("button", { name: /PDF Report/i });
    fireEvent.click(pdfBtn);
    expect(reportsApi.downloadReportFile).toHaveBeenCalledWith(
      "enrolment-by-state-course",
      "pdf",
      expect.anything()
    );
  });
});
