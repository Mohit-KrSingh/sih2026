import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import * as authModule from "../auth/AuthContext";
import * as submissionsApi from "../api/submissions";
import { SubmitPage } from "../pages/SubmitPage";
import type {
  SubmissionGateResponse,
  SubmissionReceiptResponse,
} from "../types/submissions";

const mockAdminUser = {
  id: 1,
  email: "admin@college.ac.in",
  role: "college_admin" as const,
  institution_id: 10,
  is_active: true,
};

const mockStaffUser = {
  id: 2,
  email: "staff@college.ac.in",
  role: "college_staff" as const,
  institution_id: 10,
  is_active: true,
};

function mockAuth(user: typeof mockAdminUser | typeof mockStaffUser) {
  vi.spyOn(authModule, "useAuth").mockReturnValue({
    user,
    token: "mock-jwt-token",
    isAuthenticated: true,
    isLoading: false,
    pendingMfa: null,
    login: vi.fn(),
    verifyMfa: vi.fn(),
    cancelMfa: vi.fn(),
    logout: vi.fn(),
    hasRole: vi.fn().mockImplementation((r) => r === user.role),
    isCollege: true,
    isAicte: false,
    isAdmin: user.role === "college_admin",
    refreshUser: vi.fn(),
  });
}

const mockBlockedGateResponse: SubmissionGateResponse = {
  institution_id: 10,
  institution_name: "Government Engineering College",
  aicte_id: "1-12345678",
  academic_year: "2026-27",
  current_status: "draft",
  is_locked: false,
  can_submit: false,
  target_status: null,
  gate_reason: "1 data error(s) must be resolved in student records.",
  blockers: [
    {
      flag_id: 101,
      rule_code: "APAAR_DOB_MISMATCH",
      level: "error",
      message: "Student DOB does not match APAAR registry.",
      fix_hint: "Verify original 10th marksheet or APAAR certificate.",
      field: "dob",
      student_id: 501,
      student_name: "Rahul Sharma",
      apaar_id: "123456789012",
      enrolment_no: "CSE-001",
      course_id: 20,
      course_name: "Computer Science",
      target_link: "/college/students/501/edit",
      reason: "Unresolved data error",
    },
    {
      flag_id: null,
      rule_code: "SEAT_DECLARATION_MISMATCH",
      level: "error",
      message: "Course Computer Science declared counts differ from student list.",
      fix_hint: "Reconcile declared counts on the Seat Declarations page.",
      field: "seat_declarations",
      course_id: 20,
      course_name: "Computer Science",
      target_link: "/college/seats",
      reason: "Seat declaration mismatch",
    },
  ],
  total_students: 65,
  total_courses: 2,
  open_errors_count: 2,
  unjustified_exceptions_count: 0,
  unjustified_warnings_count: 0,
  justified_exceptions_count: 0,
  justified_warnings_count: 0,
  seat_mismatch_detected: true,
};

const mockReadyGateResponse: SubmissionGateResponse = {
  institution_id: 10,
  institution_name: "Government Engineering College",
  aicte_id: "1-12345678",
  academic_year: "2026-27",
  current_status: "draft",
  is_locked: false,
  can_submit: true,
  target_status: "submitted_with_exceptions",
  gate_reason: "All errors resolved and exceptions justified.",
  blockers: [],
  total_students: 68,
  total_courses: 2,
  open_errors_count: 0,
  unjustified_exceptions_count: 0,
  unjustified_warnings_count: 0,
  justified_exceptions_count: 1,
  justified_warnings_count: 0,
  seat_mismatch_detected: false,
};

const mockReceiptResponse: SubmissionReceiptResponse = {
  institution_id: 10,
  institution_name: "Government Engineering College",
  aicte_id: "1-12345678",
  academic_year: "2026-27",
  submission_id: 99,
  receipt_no: "REC-2026-27-1-12345678-A1B2C3",
  status: "submitted_with_exceptions",
  submitted_at: "2026-10-27T14:30:00Z",
  submitted_by_email: "admin@college.ac.in",
  submitted_by_name: "admin@college.ac.in",
  declaration_text: "I confirm this data is correct and complete as authorized by the head.",
  total_students: 68,
  regular_students: 60,
  supernumerary_students: 8,
  courses_count: 2,
  justified_exceptions_count: 1,
  is_locked: true,
};

describe("SubmitPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders blocked submit gate and lists blockers with links to exact rows", async () => {
    mockAuth(mockAdminUser);
    vi.spyOn(submissionsApi, "getSubmissionGate").mockResolvedValue(mockBlockedGateResponse);

    render(
      <BrowserRouter>
        <SubmitPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Final Data Submission")).toBeInTheDocument();
      expect(screen.getByText(/Submission Gate Blocked/i)).toBeInTheDocument();
    });

    // Check metric cards
    expect(screen.getByText("65")).toBeInTheDocument(); // total students
    expect(screen.getByText("2")).toBeInTheDocument(); // open errors count

    // Check blocker rows
    expect(screen.getByText("APAAR_DOB_MISMATCH")).toBeInTheDocument();
    expect(screen.getByText("SEAT_DECLARATION_MISMATCH")).toBeInTheDocument();
    expect(screen.getByText("Rahul Sharma")).toBeInTheDocument();

    // Verify deep links to exact rows
    const resolveLinks = screen.getAllByRole("link", { name: /resolve/i });
    expect(resolveLinks[0]).toHaveAttribute("href", "/college/students/501/edit");
    expect(resolveLinks[1]).toHaveAttribute("href", "/college/seats");
  });

  it("renders ready gate with declaration affirmation and OTP flow for college_admin", async () => {
    mockAuth(mockAdminUser);
    vi.spyOn(submissionsApi, "getSubmissionGate").mockResolvedValue(mockReadyGateResponse);
    vi.spyOn(submissionsApi, "requestDeclarationOtp").mockResolvedValue({
      status: "sent",
      recipient: "admin@college.ac.in",
      channel: "email",
      purpose: "submission_declaration_10_2026-27",
      expires_in: 300,
      message: "OTP sent",
    });

    render(
      <BrowserRouter>
        <SubmitPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Submit Gate Passed: Ready for Final Submission/i)).toBeInTheDocument();
    });

    // Declaration checkbox and OTP request button
    const requestOtpBtn = screen.getByRole("button", { name: /request declaration otp/i });
    expect(requestOtpBtn).toBeInTheDocument();

    // Click request OTP
    fireEvent.click(requestOtpBtn);

    await waitFor(() => {
      expect(submissionsApi.requestDeclarationOtp).toHaveBeenCalledWith(10, "2026-27");
      expect(screen.getByText(/Verification OTP delivered to/i)).toBeInTheDocument();
    });

    // Submit button should be disabled until checkbox checked and 6 digits entered
    const submitBtn = screen.getByRole("button", { name: /submit & lock data/i });
    expect(submitBtn).toBeDisabled();

    // Check declaration checkbox
    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();

    // Enter 6-digit OTP
    const otpInput = screen.getByPlaceholderText("Enter 6-digit OTP");
    fireEvent.change(otpInput, { target: { value: "123456" } });

    expect(submitBtn).not.toBeDisabled();
  });

  it("restricts submission when user role is college_staff", async () => {
    mockAuth(mockStaffUser);
    vi.spyOn(submissionsApi, "getSubmissionGate").mockResolvedValue(mockReadyGateResponse);

    render(
      <BrowserRouter>
        <SubmitPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Role Restriction: College Admin Only/i)).toBeInTheDocument();
    });

    // Staff cannot click submit button
    const submitBtn = screen.getByRole("button", { name: /submit & lock data/i });
    expect(submitBtn).toBeDisabled();
  });

  it("submits successfully and renders locked receipt card with receipt number", async () => {
    mockAuth(mockAdminUser);
    vi.spyOn(submissionsApi, "getSubmissionGate")
      .mockResolvedValueOnce(mockReadyGateResponse)
      .mockResolvedValue({
        ...mockReadyGateResponse,
        is_locked: true,
        receipt_no: mockReceiptResponse.receipt_no,
      });
    vi.spyOn(submissionsApi, "requestDeclarationOtp").mockResolvedValue({
      status: "sent",
      recipient: "admin@college.ac.in",
      channel: "email",
      purpose: "submission_declaration_10_2026-27",
      expires_in: 300,
      message: "OTP sent",
    });
    vi.spyOn(submissionsApi, "submitAnnualData").mockResolvedValue(mockReceiptResponse);

    render(
      <BrowserRouter>
        <SubmitPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Submit Gate Passed/i)).toBeInTheDocument();
    });

    // Request OTP
    fireEvent.click(screen.getByRole("button", { name: /request declaration otp/i }));

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Enter 6-digit OTP")).not.toBeDisabled();
    });

    // Confirm checkbox and enter OTP
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.change(screen.getByPlaceholderText("Enter 6-digit OTP"), {
      target: { value: "654321" },
    });

    // Submit
    const submitBtn = screen.getByRole("button", { name: /submit & lock data/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(submissionsApi.submitAnnualData).toHaveBeenCalledWith(10, {
        academic_year: "2026-27",
        confirmed_declaration: true,
        declaration_text: expect.any(String),
        otp_code: "654321",
      });
      // Receipt Card appears
      expect(screen.getByText("Official AICTE Submission Receipt")).toBeInTheDocument();
      expect(screen.getByText("REC-2026-27-1-12345678-A1B2C3")).toBeInTheDocument();
      expect(screen.getByText(/Central Repository Locked/i)).toBeInTheDocument();
    });
  });
});
