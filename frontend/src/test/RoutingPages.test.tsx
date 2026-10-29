import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { StudentDetailPage } from "../pages/StudentDetailPage";
import { FlagDetailPage } from "../pages/FlagDetailPage";
import { ReviewItemDetailPage } from "../pages/ReviewItemDetailPage";
import { SubmissionDetailPage } from "../pages/SubmissionDetailPage";
import { StaffManagementPage } from "../pages/StaffManagementPage";
import { AicteVerifiersPage } from "../pages/AicteVerifiersPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { AppLayout } from "../components/layout/AppLayout";
import { AuthContext } from "../auth/AuthContext";
import type { User } from "../types/auth";

// Mocks for API modules
vi.mock("../api/students", () => ({
  getStudent: vi.fn().mockResolvedValue({
    id: 42,
    institution_id: 1,
    apaar_id: "999988887777",
    name: "Aaditya Patil",
    dob: "2004-05-15",
    gender: "Male",
    course_id: 10,
    academic_year: "2026-27",
    enrolment_no: "EN-2026-042",
    admission_date: "2026-07-15",
    admission_mode: "State counselling",
    seat_type: "Regular",
    reservation_category: "General",
    nri: "No",
    oci: "No",
    foreign_national: "No",
    country: null,
    status: "flagged",
    course: {
      id: 10,
      name: "Computer Science & Engineering",
      branch: "CSE",
      level: "UG",
    },
  }),
}));

vi.mock("../api/justifications", () => ({
  getInstitutionFlags: vi.fn().mockResolvedValue({
    total: 1,
    items: [
      {
        id: 101,
        rule_code: "EXC_OVER_INTAKE",
        level: "exception",
        field: "seat_type",
        message: "Course intake exceeds approved capacity by 2 seats",
        fix_hint: "Submit university sanction letter or reduce seats",
        status: "open",
        requires_justification: true,
        student_id: 42,
        student: {
          id: 42,
          name: "Aaditya Patil",
          apaar_id: "999988887777",
          enrolment_no: "EN-2026-042",
        },
        justifications: [],
      },
    ],
  }),
  createJustification: vi.fn().mockResolvedValue({ status: "success" }),
  deleteJustification: vi.fn().mockResolvedValue({ status: "deleted" }),
  downloadJustificationDocument: vi.fn().mockResolvedValue(new Blob(["mock-pdf"])),
}));

vi.mock("../api/review", () => ({
  fetchReviewItemDetail: vi.fn().mockResolvedValue({
    id: 5,
    submission_id: 12,
    institution_name: "Mumbai Metropolitan Institute of Technology",
    institution_aicte_id: "1-10001",
    academic_year: "2026-27",
    status: "pending",
    total_students: 240,
    regular_students: 220,
    supernumerary_students: 20,
    submitted_at: "2026-09-15T10:00:00Z",
    flags: [
      {
        id: 202,
        rule_code: "EXC_OVER_INTAKE",
        level: "exception",
        message: "Supernumerary quota requires High Court sanction",
        status: "justified",
        justifications: [
          {
            id: 88,
            reason: "Interim sanction granted by High Court order #HC-9821",
            document_filename: "court_order.pdf",
            created_at: "2026-09-14T09:00:00Z",
          },
        ],
      },
    ],
  }),
  submitReviewDecision: vi.fn().mockResolvedValue({ status: "success" }),
  getReviewDocumentDownloadUrl: vi.fn().mockReturnValue("/mock-url"),
}));

vi.mock("../api/submissions", () => ({
  getSubmissionReceipt: vi.fn().mockResolvedValue({
    institution_id: 1,
    institution_name: "Mumbai Metropolitan Institute of Technology",
    aicte_id: "1-10001",
    academic_year: "2026-27",
    submission_id: 12,
    receipt_no: "REC-2026-10001-A9B2C3",
    status: "submitted",
    submitted_at: "2026-09-15T12:00:00Z",
    submitted_by_email: "admin@mmit-mumbai.ac.in",
    declaration_text: "I confirm this data is correct and complete as authorized.",
    total_students: 240,
    regular_students: 220,
    supernumerary_students: 20,
    courses_count: 5,
    justified_exceptions_count: 1,
    is_locked: true,
  }),
  getSubmissionGate: vi.fn().mockResolvedValue({
    institution_id: 1,
    institution_name: "Mumbai Metropolitan Institute of Technology",
    aicte_id: "1-10001",
    academic_year: "2026-27",
    current_status: "submitted",
    is_locked: true,
    can_submit: false,
    total_students: 240,
    receipt_no: "REC-2026-10001-A9B2C3",
  }),
}));

const mockCollegeUser: User = {
  id: 1,
  email: "admin@college.edu.in",
  role: "college_admin",
  institution_id: 1,
  is_active: true,
};

const mockAicteUser: User = {
  id: 2,
  email: "officer@aicte-india.org",
  role: "aicte_officer",
  is_active: true,
};

function renderWithAuth(ui: React.ReactElement, user: User = mockCollegeUser) {
  const authValue = {
    user,
    token: "mock-token",
    isAuthenticated: true,
    isLoading: false,
    pendingMfa: null,
    login: vi.fn(),
    verifyMfa: vi.fn(),
    cancelMfa: vi.fn(),
    logout: vi.fn(),
    hasRole: () => true,
    isCollege: user.role.startsWith("college"),
    isAicte: user.role.startsWith("aicte"),
    isAdmin: user.role.includes("admin"),
    refreshUser: vi.fn(),
  };

  return render(<AuthContext.Provider value={authValue}>{ui}</AuthContext.Provider>);
}

describe("T43: Separate Pages, Real URLs, Detail Views & Navigation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders StudentDetailPage with APAAR ID, quotas, flags, and back link to directory", async () => {
    renderWithAuth(
      <MemoryRouter initialEntries={["/college/students/42"]}>
        <Routes>
          <Route path="/college/students/:id" element={<StudentDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Assert student details load
    await waitFor(() => {
      expect(screen.getByText("Aaditya Patil")).toBeInTheDocument();
    });
    expect(screen.getByText("999988887777")).toBeInTheDocument();
    expect(screen.getByText("Back to Student Directory")).toBeInTheDocument();
    expect(screen.getByText("Validation Flags for this Student")).toBeInTheDocument();
    expect(screen.getByText("EXC_OVER_INTAKE")).toBeInTheDocument();
    expect(document.title).toContain("Aaditya Patil - Student Record");
  });

  it("renders FlagDetailPage with rule details, fix guidance, and back link to flags list", async () => {
    renderWithAuth(
      <MemoryRouter initialEntries={["/college/validation/101"]}>
        <Routes>
          <Route path="/college/validation/:flagId" element={<FlagDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("EXC_OVER_INTAKE")).toBeInTheDocument();
    });
    expect(screen.getByText("Back to Validation Flags")).toBeInTheDocument();
    expect(screen.getByText("Course intake exceeds approved capacity by 2 seats")).toBeInTheDocument();
    expect(screen.getByText("Aaditya Patil")).toBeInTheDocument();
    await waitFor(() => {
      expect(document.title).toContain("Flag: EXC_OVER_INTAKE");
    });
  });

  it("renders ReviewItemDetailPage with submission metrics, decision actions, and back link", async () => {
    renderWithAuth(
      <MemoryRouter initialEntries={["/aicte/review/5"]}>
        <Routes>
          <Route path="/aicte/review/:id" element={<ReviewItemDetailPage />} />
        </Routes>
      </MemoryRouter>,
      mockAicteUser
    );

    await waitFor(() => {
      expect(screen.getByText("Review Item #5")).toBeInTheDocument();
    });
    expect(screen.getByText("Back to Review Queue")).toBeInTheDocument();
    expect(screen.getAllByText("Mumbai Metropolitan Institute of Technology").length).toBeGreaterThan(0);
    expect(screen.getByText("Accept & Certify")).toBeInTheDocument();
    expect(screen.getByText("Raise Inquiry")).toBeInTheDocument();
    expect(document.title).toContain("Review Item #5");
  });

  it("renders SubmissionDetailPage with formal receipt token and back link", async () => {
    renderWithAuth(
      <MemoryRouter initialEntries={["/college/submissions/12"]}>
        <Routes>
          <Route path="/college/submissions/:id" element={<SubmissionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText("REC-2026-10001-A9B2C3").length).toBeGreaterThan(0);
      expect(document.title).toContain("Receipt: REC-2026-10001-A9B2C3");
    });
    expect(screen.getByText("Back to Submission Gate")).toBeInTheDocument();
    expect(screen.getByText("AICTE Statutory Filing Confirmation")).toBeInTheDocument();
  });

  it("renders StaffManagementPage with RBAC matrix and invite modal for college_admin", async () => {
    renderWithAuth(
      <MemoryRouter initialEntries={["/college/staff"]}>
        <Routes>
          <Route path="/college/staff" element={<StaffManagementPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Staff Account Management")).toBeInTheDocument();
    expect(screen.getByText("Role-Based Access Control (RBAC) Matrix")).toBeInTheDocument();
    expect(document.title).toContain("Staff Account Management");

    // Click Add Staff Member
    const addBtn = screen.getByRole("button", { name: /Add Staff Member/i });
    fireEvent.click(addBtn);
    expect(screen.getByText("Add Staff Account")).toBeInTheDocument();
  });

  it("renders AicteVerifiersPage with registered verifier organisations and DPDP compliance", async () => {
    renderWithAuth(
      <MemoryRouter initialEntries={["/aicte/verifiers"]}>
        <Routes>
          <Route path="/aicte/verifiers" element={<AicteVerifiersPage />} />
        </Routes>
      </MemoryRouter>,
      mockAicteUser
    );

    expect(screen.getByText("Third-Party Verifier Management")).toBeInTheDocument();
    expect(screen.getByText("TCS iON Verification Services")).toBeInTheDocument();
    expect(screen.getByText("HirePro Background Checks Ltd")).toBeInTheDocument();
    expect(screen.getByText("DPDP Act 2023 & Consent Protection Architecture")).toBeInTheDocument();
    expect(document.title).toContain("Third-Party Verifier Management");
  });

  it("renders NotFoundPage on unknown route with a link home", () => {
    render(
      <MemoryRouter initialEntries={["/some/non-existent-path"]}>
        <Routes>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Page Not Found")).toBeInTheDocument();
    expect(screen.getByText("HTTP 404 Not Found")).toBeInTheDocument();
    const homeBtn = screen.getByRole("button", { name: /Return to home/i });
    expect(homeBtn).toBeInTheDocument();
    expect(document.title).toContain("404 Page Not Found");
  });

  it("highlights persistent navigation tab on sub-routes", () => {
    renderWithAuth(
      <MemoryRouter initialEntries={["/college/students/42"]}>
        <AppLayout>
          <div>Page Content</div>
        </AppLayout>
      </MemoryRouter>
    );

    const studentsTab = screen.getByRole("link", { name: /Students/i });
    expect(studentsTab).toBeInTheDocument();
    // Prefix matching highlights the active item with UX4G semantic primary token and aria-current
    expect(studentsTab).toHaveAttribute("aria-current", "page");
    expect(studentsTab.className).toContain("ux4g-bg-primary-soft");
  });
});
