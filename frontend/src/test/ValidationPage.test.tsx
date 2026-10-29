import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import * as authModule from "../auth/AuthContext";
import * as justificationsApi from "../api/justifications";
import { ValidationPage } from "../pages/ValidationPage";
import type { InstitutionFlagsListResponse } from "../types/validation";

const mockUser = {
  id: 1,
  email: "admin@college.ac.in",
  role: "college_admin" as const,
  institution_id: 10,
  is_active: true,
};

const mockFlagsResponse: InstitutionFlagsListResponse = {
  institution_id: 10,
  academic_year: "2026-27",
  summary: {
    total_flags: 3,
    open_count: 2,
    justified_count: 1,
    resolved_count: 0,
    error_count: 1,
    exception_count: 1,
    warning_count: 1,
    info_count: 0,
    blocking_count: 1,
    can_submit: false,
  },
  items: [
    {
      id: 101,
      rule_code: "NAME_REQUIRED",
      level: "error",
      field: "name",
      message: "Student legal name is missing.",
      fix_hint: "Provide the student's legal name matching their official APAAR record.",
      audience: "both",
      requires_justification: false,
      status: "open",
      student: {
        id: 501,
        apaar_id: "123456789012",
        name: "Missing Name",
        enrolment_no: "ENR-001",
        academic_year: "2026-27",
        course_name: "Computer Science",
      },
      justifications: [],
      created_at: "2026-09-01T10:00:00Z",
      updated_at: "2026-09-01T10:00:00Z",
    },
    {
      id: 102,
      rule_code: "INTAKE_EXCEEDED",
      level: "exception",
      field: null,
      message: "Regular student admissions exceed approved intake by 8.",
      fix_hint: "Withdraw surplus regular admissions or submit written justification.",
      audience: "both",
      requires_justification: true,
      status: "open",
      course: {
        id: 201,
        name: "Computer Science and Engineering",
        branch: "Computer Science",
        level: "UG",
      },
      justifications: [],
      created_at: "2026-09-01T10:00:00Z",
      updated_at: "2026-09-01T10:00:00Z",
    },
    {
      id: 103,
      rule_code: "AGE_OUT_OF_RANGE",
      level: "warning",
      field: "dob",
      message: "Student age is outside typical UG band.",
      fix_hint: "Verify date of birth or attach institutional verification.",
      audience: "both",
      requires_justification: false,
      status: "justified",
      student: {
        id: 502,
        apaar_id: "987654321098",
        name: "Aarav Sharma",
        enrolment_no: "ENR-002",
        academic_year: "2026-27",
      },
      justifications: [
        {
          id: 301,
          flag_id: 103,
          text: "Candidate completed higher secondary late due to national sports participation.",
          document_ref: "justifications/10/flag_103_sports_cert.pdf",
          document_url: "/api/v1/institutions/10/justifications/301/document",
          author_name: "admin@college.ac.in",
          author_role: "college_admin",
          at: "2026-09-02T12:00:00Z",
          created_at: "2026-09-02T12:00:00Z",
          updated_at: "2026-09-02T12:00:00Z",
        },
      ],
      created_at: "2026-09-01T10:00:00Z",
      updated_at: "2026-09-01T10:00:00Z",
    },
  ],
};

describe("ValidationPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(authModule, "useAuth").mockReturnValue({
      user: mockUser,
      token: "mock-jwt-token",
      isAuthenticated: true,
      isLoading: false,
      pendingMfa: null,
      login: vi.fn(),
      verifyMfa: vi.fn(),
      cancelMfa: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(true),
      isCollege: true,
      isAicte: false,
      isAdmin: true,
      refreshUser: vi.fn(),
    });

    vi.spyOn(justificationsApi, "getInstitutionFlags").mockResolvedValue(mockFlagsResponse);
  });

  it("renders validation flags, summary KPI cards, and gate blockers", async () => {
    render(
      <BrowserRouter>
        <ValidationPage />
      </BrowserRouter>
    );

    expect(screen.getByText("Validation Flags & Justifications")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Total Flags")).toBeInTheDocument();
      expect(screen.getByText("Submit Blockers")).toBeInTheDocument();
      expect(screen.getAllByText("Justified").length).toBeGreaterThan(0);
    });

    // Check flag table entries
    expect(screen.getByText("NAME_REQUIRED")).toBeInTheDocument();
    expect(screen.getByText("INTAKE_EXCEEDED")).toBeInTheDocument();
    expect(screen.getByText("AGE_OUT_OF_RANGE")).toBeInTheDocument();

    // Check gate status banner shows blocked
    expect(screen.getByText(/Submission Gate: BLOCKED/i)).toBeInTheDocument();
  });

  it("distinguishes error flags from exception flags: errors cannot be justified", async () => {
    render(
      <BrowserRouter>
        <ValidationPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("NAME_REQUIRED")).toBeInTheDocument();
    });

    // Error flag must have "Must Fix Data" / "Fix in Record"
    expect(screen.getByText("Must Fix Data")).toBeInTheDocument();
    expect(screen.getByText("Fix in Record")).toBeInTheDocument();

    // Exception flag has "Add Justification"
    expect(screen.getByText("Add Justification")).toBeInTheDocument();
  });

  it("filters flags when level tab is clicked", async () => {
    render(
      <BrowserRouter>
        <ValidationPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Exceptions")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Exceptions"));

    expect(justificationsApi.getInstitutionFlags).toHaveBeenCalledWith(
      10,
      expect.objectContaining({ level: "exception" })
    );
  });

  it("opens justification modal for an exception and submits justification", async () => {
    const createJustificationMock = vi
      .spyOn(justificationsApi, "createJustification")
      .mockResolvedValue({
        id: 401,
        flag_id: 102,
        text: "Approved by state admission authority under quota allotment.",
        document_ref: null,
        at: "2026-09-10T00:00:00Z",
        created_at: "2026-09-10T00:00:00Z",
        updated_at: "2026-09-10T00:00:00Z",
      });

    render(
      <BrowserRouter>
        <ValidationPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("INTAKE_EXCEEDED")).toBeInTheDocument();
    });

    // Click "Add Justification" on INTAKE_EXCEEDED
    fireEvent.click(screen.getByText("Add Justification"));

    // Modal opens
    expect(screen.getByText("Statutory Justification & Evidence")).toBeInTheDocument();
    expect(
      screen.getAllByText("Regular student admissions exceed approved intake by 8.").length
    ).toBeGreaterThan(0);

    // Fill justification text
    const textarea = screen.getByPlaceholderText(/State the regulatory basis/i);
    fireEvent.change(textarea, {
      target: {
        value: "Approved by state admission authority under quota allotment.",
      },
    });

    // Submit form
    fireEvent.click(screen.getByText("Save Justification"));

    await waitFor(() => {
      expect(createJustificationMock).toHaveBeenCalledWith(
        10,
        102,
        "Approved by state admission authority under quota allotment.",
        null
      );
    });
  });

  it("allows viewing and downloading attached documents on justified flags", async () => {
    const downloadMock = vi
      .spyOn(justificationsApi, "downloadJustificationDocument")
      .mockResolvedValue({
        blob: new Blob(["sample content"], { type: "application/pdf" }),
        filename: "flag_103_sports_cert.pdf",
      });

    // Mock createObjectURL
    window.URL.createObjectURL = vi.fn().mockReturnValue("blob:http://localhost/dummy");
    window.URL.revokeObjectURL = vi.fn();

    render(
      <BrowserRouter>
        <ValidationPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("View / Edit Justification")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("View / Edit Justification"));

    // Modal displays existing justifications
    expect(screen.getByText("Existing Justification Records")).toBeInTheDocument();
    expect(screen.getByText(/sports participation/i)).toBeInTheDocument();

    // Click Download
    const downloadBtn = screen.getByText("Download");
    fireEvent.click(downloadBtn);

    expect(downloadMock).toHaveBeenCalledWith(10, 301);
  });
});
