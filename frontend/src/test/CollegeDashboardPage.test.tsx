import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import * as authModule from "../auth/AuthContext";
import * as seatsApi from "../api/seats";
import * as justificationsApi from "../api/justifications";
import * as submissionsApi from "../api/submissions";
import * as reviewApi from "../api/review";
import * as institutionsApi from "../api/institutions";
import { CollegeDashboardPage } from "../pages/CollegeDashboardPage";
import type { InstitutionFlagsListResponse } from "../types/validation";
import type { SubmissionGateResponse, SubmissionReceiptResponse } from "../types/submissions";

const mockCollegeUser = {
  id: 1,
  email: "admin@college.edu",
  role: "college_admin" as const,
  institution_id: 101,
  is_active: true,
};

const mockSeatData: seatsApi.InstitutionSeatDeclarationResponse = {
  institution_id: 101,
  academic_year: "2026-27",
  total_approved_intake: 180,
  total_supernumerary_allowed: 18,
  total_declared_regular: 150,
  total_declared_supernumerary: 10,
  total_declared: 160,
  total_enrolled: 150,
  courses: [
    {
      course_id: 1,
      course_name: "Computer Science & Engineering",
      branch: "Computer Engineering",
      level: "UG",
      duration_years: 4,
      academic_year: "2026-27",
      approved_intake: 120,
      supernumerary_seats_allowed: 12,
      regular_admitted: 110,
      supernumerary_admitted: 8,
      nri_count: 5,
      oci_count: 0,
      fn_count: 0,
      total_declared: 118,
      calculated_enrolment: 118,
      calculated_regular: 110,
      calculated_supernumerary: 8,
      status: "declared",
      status_badge: "within_limit",
      overshoot: 0,
      supernumerary_overshoot: 0,
      flags: [],
      updated_at: new Date().toISOString(),
    },
    {
      course_id: 2,
      course_name: "Electronics Engineering",
      branch: "ECE",
      level: "UG",
      duration_years: 4,
      academic_year: "2026-27",
      approved_intake: 60,
      supernumerary_seats_allowed: 6,
      regular_admitted: 70,
      supernumerary_admitted: 2,
      nri_count: 0,
      oci_count: 0,
      fn_count: 0,
      total_declared: 72,
      calculated_enrolment: 72,
      calculated_regular: 70,
      calculated_supernumerary: 2,
      status: "draft",
      status_badge: "over_by_n",
      overshoot: 10,
      supernumerary_overshoot: 0,
      flags: [
        {
          rule_code: "INTAKE_EXCEEDED",
          level: "exception",
          message: "Regular admission (70) exceeds approved intake (60) by 10.",
          fix_hint: "Review records or obtain AICTE sanction.",
        },
      ],
      updated_at: new Date().toISOString(),
    },
  ],
};

const mockFlagsData: InstitutionFlagsListResponse = {
  institution_id: 101,
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
      id: 501,
      student_id: 1001,
      course_id: 1,
      rule_code: "APAAR_DOB_MISMATCH",
      level: "error",
      message: "Student DOB does not match APAAR registry.",
      fix_hint: "Verify official birth certificate.",
      field: "dob",
      audience: "both",
      requires_justification: false,
      status: "open",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      justifications: [],
    },
    {
      id: 502,
      student_id: null,
      course_id: 2,
      rule_code: "INTAKE_EXCEEDED",
      level: "exception",
      message: "Regular admission (70) exceeds approved intake (60) by 10.",
      fix_hint: "Provide AICTE expansion order or court directive.",
      field: null,
      audience: "both",
      requires_justification: true,
      status: "justified",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      justifications: [
        {
          id: 99,
          flag_id: 502,
          text: "Sanctioned by State High Court interim order W.P. 1234/2026.",
          document_ref: "court_order.pdf",
          document_url: "/docs/court_order.pdf",
          by_user: 1,
          author_name: "Principal Officer",
          author_role: "college_admin",
          at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
    },
    {
      id: 503,
      student_id: 1002,
      course_id: 1,
      rule_code: "APAAR_NAME_MISMATCH",
      level: "warning",
      message: "Minor spelling variance in student name against registry.",
      fix_hint: "Ensure identity document matches.",
      field: "name",
      audience: "both",
      requires_justification: false,
      status: "open",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      justifications: [],
    },
  ],
};

const mockGateDraftData: SubmissionGateResponse = {
  institution_id: 101,
  institution_name: "Alpha College of Technology",
  aicte_id: "1-12345678",
  academic_year: "2026-27",
  current_status: "draft",
  is_locked: false,
  can_submit: false,
  target_status: null,
  gate_reason: "1 blocking error must be resolved.",
  blockers: [
    {
      flag_id: 501,
      rule_code: "APAAR_DOB_MISMATCH",
      level: "error",
      message: "Student DOB does not match APAAR registry.",
      student_id: 1001,
      student_name: "Rahul Kumar",
      apaar_id: "111122223333",
      target_link: "/college/students?search=1001",
      reason: "Error-level flag open",
    },
  ],
  total_students: 150,
  total_courses: 2,
  open_errors_count: 1,
  unjustified_exceptions_count: 0,
  unjustified_warnings_count: 0,
  justified_exceptions_count: 1,
  justified_warnings_count: 0,
  seat_mismatch_detected: false,
};

const mockGateLockedData: SubmissionGateResponse = {
  ...mockGateDraftData,
  current_status: "submitted",
  is_locked: true,
  can_submit: false,
  receipt_no: "REC-2026-27-1-12345678-ABC99",
  submitted_at: "2026-10-27T10:00:00Z",
  submitted_by_name: "admin@college.edu",
};

const mockReceiptData: SubmissionReceiptResponse = {
  submission_id: 10,
  institution_id: 101,
  institution_name: "Alpha College of Technology",
  aicte_id: "1-12345678",
  academic_year: "2026-27",
  status: "submitted",
  is_locked: true,
  receipt_no: "REC-2026-27-1-12345678-ABC99",
  submitted_at: "2026-10-27T10:00:00Z",
  submitted_by_email: "admin@college.edu",
  declaration_text: "DEC-101-2026-27",
  total_students: 150,
  regular_students: 140,
  supernumerary_students: 10,
  courses_count: 2,
  justified_exceptions_count: 1,
};

const mockQueriesData = {
  total: 1,
  items: [
    {
      id: 701,
      submission_id: 10,
      institution_id: 101,
      institution_name: "Alpha College of Technology",
      academic_year: "2026-27",
      officer_name: "Dr. AICTE Reviewer",
      message: "Please upload the revised AICTE intake sanction for Electronics Engineering.",
      state: "pending" as const,
      created_at: new Date().toISOString(),
      flags: [],
    },
  ],
};

const mockNotificationsData: institutionsApi.NotificationItem[] = [
  {
    id: 901,
    institution_id: 101,
    type: "duplicate_enrolment_detected",
    payload: {
      apaar_id: "999988887777",
      student_name: "Aakash Verma",
      other_college_name: "Beta Institute of Technology",
      message: "Student is actively enrolled in Computer Engineering at Beta Institute of Technology.",
    },
    read_at: null,
    created_at: new Date().toISOString(),
  },
  {
    id: 902,
    institution_id: 101,
    type: "intake_updated",
    payload: {
      course_name: "Computer Science & Engineering",
      new_intake: 120,
      message: "AICTE approved intake verified at 120 seats.",
    },
    read_at: null,
    created_at: "2026-10-27T08:00:00Z",
  },
];

describe("CollegeDashboardPage UI Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(authModule, "useAuth").mockReturnValue({
      user: mockCollegeUser,
      token: "fake-jwt-token",
      isLoading: false,
      isAuthenticated: true,
      pendingMfa: null,
      isCollege: true,
      isAicte: false,
      isAdmin: false,
      login: vi.fn(),
      verifyMfa: vi.fn(),
      cancelMfa: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn(),
      refreshUser: vi.fn(),
    });

    vi.spyOn(seatsApi, "getInstitutionSeatDeclarations").mockResolvedValue(mockSeatData);
    vi.spyOn(justificationsApi, "getInstitutionFlags").mockResolvedValue(mockFlagsData);
    vi.spyOn(submissionsApi, "getSubmissionGate").mockResolvedValue(mockGateDraftData);
    vi.spyOn(submissionsApi, "getSubmissionReceipt").mockResolvedValue(mockReceiptData);
    vi.spyOn(reviewApi, "fetchCollegeQueries").mockResolvedValue(mockQueriesData as any);
    vi.spyOn(institutionsApi, "getInstitutionNotifications").mockResolvedValue(mockNotificationsData);
    vi.spyOn(institutionsApi, "markNotificationRead").mockResolvedValue({
      status: "success",
      id: 901,
      read_at: new Date().toISOString(),
    });
    vi.spyOn(institutionsApi, "markAllNotificationsRead").mockResolvedValue({
      status: "success",
      marked_read_count: 1,
    });
  });

  it("renders CollegeDashboardPage with KPI summary cards and course summary table with lock icons", async () => {
    render(
      <BrowserRouter>
        <CollegeDashboardPage />
      </BrowserRouter>
    );

    // Header and Welcome
    expect(await screen.findByText("Institutional Dashboard")).toBeInTheDocument();
    expect(screen.getByText(/admin@college\.edu/)).toBeInTheDocument();

    // Top KPI cards
    expect(screen.getByText("Approved Courses")).toBeInTheDocument();
    expect(screen.getAllByText("Total Admitted").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Validation Flags")).toBeInTheDocument();
    expect(screen.getByText("AICTE Inquiries")).toBeInTheDocument();

    // Course Summary Table
    expect(screen.getByText("Course Summary Table")).toBeInTheDocument();
    expect(screen.getByText("Computer Science & Engineering")).toBeInTheDocument();
    expect(screen.getByText("Electronics Engineering")).toBeInTheDocument();

    // Approved intake with lock icon
    expect(screen.getAllByText("120").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("60")).toBeInTheDocument();

    // Intake Status Badges
    expect(screen.getByText("Within limit")).toBeInTheDocument();
    expect(screen.getByText("Over by 10")).toBeInTheDocument();
  });

  it("renders pending validation flags grouped by level with target links and filter tabs", async () => {
    render(
      <BrowserRouter>
        <CollegeDashboardPage />
      </BrowserRouter>
    );

    expect(await screen.findByText("Pending Validation Flags")).toBeInTheDocument();

    // Flag badges and codes
    expect(screen.getByText("APAAR_DOB_MISMATCH")).toBeInTheDocument();
    expect(screen.getAllByText("INTAKE_EXCEEDED").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("APAAR_NAME_MISMATCH")).toBeInTheDocument();

    // Status indicators
    expect(screen.getByText("✓ Justified")).toBeInTheDocument();
    expect(screen.getAllByText("Student DOB does not match APAAR registry.").length).toBeGreaterThanOrEqual(1);

    // Row links
    expect(screen.getByText("Row #1001")).toBeInTheDocument();
    expect(screen.getByText("Course #2")).toBeInTheDocument();

    // Filter by level tab
    const errorsTab = screen.getByRole("button", { name: /Errors/i });
    fireEvent.click(errorsTab);

    // Only error flag visible
    expect(screen.getByText("APAAR_DOB_MISMATCH")).toBeInTheDocument();
    expect(screen.queryByText("APAAR_NAME_MISMATCH")).not.toBeInTheDocument();
  });

  it("renders submission gate blockers and warning state when in draft", async () => {
    render(
      <BrowserRouter>
        <CollegeDashboardPage />
      </BrowserRouter>
    );

    expect(await screen.findByText("Submission Blocked by Validation Issues")).toBeInTheDocument();
    expect(screen.getAllByText("Student DOB does not match APAAR registry.").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Review Submission Blockers")).toBeInTheDocument();
  });

  it("renders official receipt and locked banner when submission is locked", async () => {
    vi.spyOn(submissionsApi, "getSubmissionGate").mockResolvedValue(mockGateLockedData);

    render(
      <BrowserRouter>
        <CollegeDashboardPage />
      </BrowserRouter>
    );

    expect(await screen.findByText("Official AICTE Central Repository Receipt")).toBeInTheDocument();
    expect(screen.getByText("REC-2026-27-1-12345678-ABC99")).toBeInTheDocument();
    expect(screen.getByText("Data Locked & Read-only")).toBeInTheDocument();
    expect(screen.getByText("View Receipt Details")).toBeInTheDocument();
  });

  it("renders pending AICTE clarification inquiries with quick action button", async () => {
    render(
      <BrowserRouter>
        <CollegeDashboardPage />
      </BrowserRouter>
    );

    expect(await screen.findByText("AICTE Clarification Inquiries")).toBeInTheDocument();
    expect(
      screen.getByText(/Please upload the revised AICTE intake sanction for Electronics Engineering/)
    ).toBeInTheDocument();
    expect(screen.getByText("Dr. AICTE Reviewer")).toBeInTheDocument();
    expect(screen.getByText("Reply to Query")).toBeInTheDocument();
  });

  it("renders system notifications feed and handles mark as read actions", async () => {
    render(
      <BrowserRouter>
        <CollegeDashboardPage />
      </BrowserRouter>
    );

    expect(await screen.findByText("Institutional Notifications")).toBeInTheDocument();
    expect(screen.getByText(/DUPLICATE ENROLMENT DETECTED/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Student is actively enrolled in Computer Engineering at Beta Institute of Technology/)
    ).toBeInTheDocument();
    expect(screen.getByText("Beta Institute of Technology")).toBeInTheDocument();

    // Mark single notification as read
    const markReadBtns = screen.getAllByRole("button", { name: "Mark as read" });
    fireEvent.click(markReadBtns[0]);

    await waitFor(() => {
      expect(institutionsApi.markNotificationRead).toHaveBeenCalledWith(101, 901);
    });

    // Mark all read button
    const markAllBtn = screen.getByRole("button", { name: "Mark All Read" });
    fireEvent.click(markAllBtn);

    await waitFor(() => {
      expect(institutionsApi.markAllNotificationsRead).toHaveBeenCalledWith(101);
    });
  });

  it("displays statutory submission workflow pipeline guide", async () => {
    render(
      <BrowserRouter>
        <CollegeDashboardPage />
      </BrowserRouter>
    );

    expect(await screen.findByText(/Statutory Data Submission Pipeline/i)).toBeInTheDocument();
    expect(screen.getByText("Seat Declarations")).toBeInTheDocument();
    expect(screen.getByText("Individual Entry")).toBeInTheDocument();
    expect(screen.getByText("Bulk CSV Upload")).toBeInTheDocument();
    expect(screen.getByText("Resolve & Justify")).toBeInTheDocument();
    expect(screen.getByText("Submit Gate")).toBeInTheDocument();
  });
});
