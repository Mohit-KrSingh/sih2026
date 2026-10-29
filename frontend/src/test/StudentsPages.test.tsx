import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import * as authModule from "../auth/AuthContext";
import * as studentsApi from "../api/students";
import * as institutionsApi from "../api/institutions";
import { StudentsListPage } from "../pages/StudentsListPage";
import { StudentFormPage } from "../pages/StudentFormPage";

const mockCollegeAdmin = {
  id: 1,
  email: "admin@alpha.edu",
  role: "college_admin" as const,
  institution_id: 10,
  is_active: true,
};

const mockCollegeViewer = {
  id: 2,
  email: "viewer@alpha.edu",
  role: "college_viewer" as const,
  institution_id: 10,
  is_active: true,
};

const mockCourses: institutionsApi.CourseResponse[] = [
  {
    id: 101,
    institution_id: 10,
    name: "Computer Science and Engineering",
    branch: "CSE",
    level: "UG",
    duration_years: 4,
    supernumerary_allowed: true,
    intakes: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: 102,
    institution_id: 10,
    name: "Mechanical Engineering",
    branch: "MECH",
    level: "UG",
    duration_years: 4,
    supernumerary_allowed: false,
    intakes: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

const mockStudentsList: studentsApi.StudentListResponse = {
  items: [
    {
      id: 1,
      institution_id: 10,
      course_id: 101,
      course_name: "Computer Science and Engineering",
      branch: "CSE",
      academic_year: "2026-27",
      apaar_id: "111122223333",
      name: "Rahul Sharma",
      dob: "2005-05-15",
      gender: "Male",
      enrolment_no: "EN26-CSE-0001",
      admission_date: "2026-08-10",
      admission_mode: "State counselling",
      seat_type: "Regular",
      reservation_category: "General",
      nri: "No",
      oci: "No",
      foreign_national: "No",
      country: null,
      status: "valid",
      is_locked: false,
      submission_id: null,
      source: "form",
      flags: [],
      created_at: "2026-08-10T00:00:00Z",
      updated_at: "2026-08-10T00:00:00Z",
    },
    {
      id: 2,
      institution_id: 10,
      course_id: 101,
      course_name: "Computer Science and Engineering",
      branch: "CSE",
      academic_year: "2026-27",
      apaar_id: "222233334444",
      name: "Flagged Student",
      dob: "2004-08-20",
      gender: "Female",
      enrolment_no: "EN26-CSE-0002",
      admission_date: "2026-08-10",
      admission_mode: "State counselling",
      seat_type: "Regular",
      reservation_category: "OBC",
      nri: "No",
      oci: "No",
      foreign_national: "No",
      country: null,
      status: "flagged",
      is_locked: false,
      submission_id: null,
      source: "form",
      flags: [
        {
          id: 501,
          rule_code: "APAAR_NAME_MISMATCH",
          level: "warning",
          field: "name",
          message: "Fuzzy name mismatch with registry",
          fix_hint: "Verify official Aadhaar/APAAR name",
          status: "open",
        },
      ],
      created_at: "2026-08-10T00:00:00Z",
      updated_at: "2026-08-10T00:00:00Z",
    },
  ],
  total: 2,
  page: 1,
  limit: 15,
  total_pages: 1,
  stats: {
    total: 2,
    valid: 1,
    flagged: 1,
    draft: 0,
    submitted: 0,
    error_flags_count: 0,
    exception_flags_count: 0,
    warning_flags_count: 1,
  },
};

describe("T20: Student Directory & Single Student Entry", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(authModule, "useAuth").mockReturnValue({
      user: mockCollegeAdmin,
      token: "mock-token",
      isAuthenticated: true,
      isLoading: false,
      pendingMfa: null,
      isCollege: true,
      isAicte: false,
      isAdmin: true,
      hasRole: () => true,
      login: vi.fn(),
      verifyMfa: vi.fn(),
      cancelMfa: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    vi.spyOn(institutionsApi, "listCourses").mockResolvedValue(mockCourses);
    vi.spyOn(studentsApi, "getStudents").mockResolvedValue(mockStudentsList);
    vi.spyOn(studentsApi, "getStudent").mockResolvedValue(mockStudentsList.items[0]);
    vi.spyOn(studentsApi, "createStudent").mockResolvedValue({
      student: mockStudentsList.items[0],
      flags: [],
      is_valid: true,
      errors_count: 0,
      exceptions_count: 0,
      warnings_count: 0,
      infos_count: 0,
    });
    vi.spyOn(studentsApi, "updateStudent").mockResolvedValue({
      student: mockStudentsList.items[0],
      flags: [],
      is_valid: true,
      errors_count: 0,
      exceptions_count: 0,
      warnings_count: 0,
      infos_count: 0,
    });
    vi.spyOn(studentsApi, "deleteStudent").mockResolvedValue({
      message: "Deleted",
      student_id: 1,
    });
  });

  describe("StudentsListPage", () => {
    it("renders students directory with summary cards, table, and actions", async () => {
      render(
        <BrowserRouter>
          <StudentsListPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Student Records Directory")).toBeInTheDocument();
        expect(screen.getByText("Rahul Sharma")).toBeInTheDocument();
        expect(screen.getByText("111122223333")).toBeInTheDocument();
        expect(screen.getByText("Flagged Student")).toBeInTheDocument();
      });

      // Overview statistics
      expect(screen.getByText("Total Enrolled")).toBeInTheDocument();
      expect(screen.getByText("Compliant (Clean)")).toBeInTheDocument();
      expect(screen.getByText("Flagged Records")).toBeInTheDocument();

      // Table headers
      expect(screen.getByText("APAAR ID")).toBeInTheDocument();
      expect(screen.getByText("Student Name")).toBeInTheDocument();
      expect(screen.getByText("Course & Branch")).toBeInTheDocument();
      expect(screen.getByText("Validation Flags")).toBeInTheDocument();
    });

    it("triggers filter updates by status and level", async () => {
      render(
        <BrowserRouter>
          <StudentsListPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Rahul Sharma")).toBeInTheDocument();
      });

      // Filter select elements
      const statusSelect = screen.getByLabelText("Record Status");
      fireEvent.change(statusSelect, { target: { value: "valid" } });

      await waitFor(() => {
        expect(studentsApi.getStudents).toHaveBeenCalledWith(
          10,
          expect.objectContaining({ status: "valid" })
        );
      });

      const levelSelect = screen.getByLabelText("Validation Level");
      fireEvent.change(levelSelect, { target: { value: "warning" } });

      await waitFor(() => {
        expect(studentsApi.getStudents).toHaveBeenCalledWith(
          10,
          expect.objectContaining({ level: "warning" })
        );
      });
    });

    it("opens delete confirmation modal and confirms deletion", async () => {
      render(
        <BrowserRouter>
          <StudentsListPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Rahul Sharma")).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole("button", { name: "Delete" });
      fireEvent.click(deleteButtons[0]);

      // Confirm modal appears
      expect(screen.getByText("Confirm Draft Deletion")).toBeInTheDocument();
      expect(
        screen.getByText(/Are you sure you want to delete the draft student record for/)
      ).toBeInTheDocument();

      const confirmBtn = screen.getByRole("button", { name: "Delete Draft" });
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(studentsApi.deleteStudent).toHaveBeenCalledWith(10, 1);
      });
    });
  });

  describe("StudentFormPage", () => {
    it("renders grouped fields: Identity, Admission, Category", async () => {
      render(
        <BrowserRouter>
          <StudentFormPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Single Student Entry")).toBeInTheDocument();
      });

      // Form Section Headers
      expect(screen.getByText("Identity Information")).toBeInTheDocument();
      expect(screen.getByText("Admission Details")).toBeInTheDocument();
      expect(screen.getByText("Category & Nationality")).toBeInTheDocument();

      // Fields
      expect(screen.getByLabelText(/APAAR ID/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Student Full Name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Date of Birth/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Approved Course & Branch/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/College Enrolment/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Reservation Category/i)).toBeInTheDocument();

      // Action button
      expect(screen.getByRole("button", { name: "Check and save" })).toBeInTheDocument();
    });

    it("conditionally displays Country field ONLY when Foreign National is Yes", async () => {
      render(
        <BrowserRouter>
          <StudentFormPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/Foreign National/i)).toBeInTheDocument();
      });

      // Country input is not rendered when Foreign National is No
      expect(screen.queryByLabelText(/Country of Origin/i)).not.toBeInTheDocument();

      // Switch Foreign National to Yes
      const fnSelect = screen.getByLabelText(/Foreign National/i);
      fireEvent.change(fnSelect, { target: { value: "Yes" } });

      // Country input now appears
      expect(screen.getByLabelText(/Country of Origin/i)).toBeInTheDocument();

      // Switch back to No -> Country input disappears
      fireEvent.change(fnSelect, { target: { value: "No" } });
      expect(screen.queryByLabelText(/Country of Origin/i)).not.toBeInTheDocument();
    });

    it("executes 'Check and save' and displays validation results", async () => {
      // Mock validation failure response
      vi.spyOn(studentsApi, "createStudent").mockResolvedValueOnce({
        student: { ...mockStudentsList.items[1], status: "flagged" },
        flags: [
          {
            rule_code: "APAAR_NOT_FOUND",
            level: "error",
            field: "apaar_id",
            message: "APAAR ID not found in registry",
            fix_hint: "Check with student",
            status: "open",
          },
        ],
        is_valid: false,
        errors_count: 1,
        exceptions_count: 0,
        warnings_count: 0,
        infos_count: 0,
      });

      render(
        <BrowserRouter>
          <StudentFormPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/APAAR ID/i)).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/APAAR ID/i), {
        target: { value: "999988887777" },
      });
      fireEvent.change(screen.getByLabelText(/Student Full Name/i), {
        target: { value: "Unknown Person" },
      });
      fireEvent.change(screen.getByLabelText(/Date of Birth/i), {
        target: { value: "2005-01-01" },
      });
      fireEvent.change(screen.getByLabelText(/College Enrolment/i), {
        target: { value: "EN26-0099" },
      });
      fireEvent.change(screen.getByLabelText(/Admission Date/i), {
        target: { value: "2026-08-01" },
      });

      const submitBtn = screen.getByRole("button", { name: "Check and save" });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(studentsApi.createStudent).toHaveBeenCalled();
        expect(screen.getByText("Draft Saved with Validation Errors")).toBeInTheDocument();
        expect(screen.getByText("APAAR ID not found in registry")).toBeInTheDocument();
        expect(screen.getByText("APAAR_NOT_FOUND")).toBeInTheDocument();
      });
    });

    it("renders edit mode when student ID is provided in route", async () => {
      render(
        <BrowserRouter>
          <Routes>
            <Route path="/college/students/:id/edit" element={<StudentFormPage />} />
          </Routes>
        </BrowserRouter>
      );

      window.history.pushState({}, "Edit Student", "/college/students/1/edit");

      render(
        <BrowserRouter>
          <Routes>
            <Route path="/college/students/:id/edit" element={<StudentFormPage />} />
          </Routes>
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(studentsApi.getStudent).toHaveBeenCalledWith(10, 1);
      });
    });

    it("disables mutation actions for college_viewer", async () => {
      vi.spyOn(authModule, "useAuth").mockReturnValue({
        user: mockCollegeViewer,
        token: "viewer-token",
        isAuthenticated: true,
        isLoading: false,
        pendingMfa: null,
        isCollege: true,
        isAicte: false,
        isAdmin: false,
        hasRole: () => false,
        login: vi.fn(),
        verifyMfa: vi.fn(),
        cancelMfa: vi.fn(),
        logout: vi.fn(),
        refreshUser: vi.fn(),
      });

      render(
        <BrowserRouter>
          <StudentFormPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Read-only mode:/i)).toBeInTheDocument();
      });

      // Submit button is hidden
      expect(screen.queryByRole("button", { name: "Check and save" })).not.toBeInTheDocument();
      // Inputs are disabled
      expect(screen.getByLabelText(/APAAR ID/i)).toBeDisabled();
      expect(screen.getByLabelText(/Student Full Name/i)).toBeDisabled();
    });
  });
});
