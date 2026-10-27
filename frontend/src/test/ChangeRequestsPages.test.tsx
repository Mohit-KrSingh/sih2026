import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { CollegeChangeRequestsPage } from "../pages/CollegeChangeRequestsPage";
import { AicteChangeRequestsPage } from "../pages/AicteChangeRequestsPage";
import * as changeRequestsApi from "../api/changeRequests";
import * as studentsApi from "../api/students";
import type { ChangeRequest } from "../types/changeRequests";

// Mock AuthContext
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: "admin@piaet-pune.edu.in",
      role: "college_admin",
      institution_id: 1,
    },
    token: "mock-token",
    isAuthenticated: true,
  }),
}));

const mockChangeRequests: ChangeRequest[] = [
  {
    id: 101,
    student_id: 501,
    student: {
      id: 501,
      apaar_id: "123456789012",
      name: "Rohan Patil",
      course_id: 10,
      course_name: "Computer Engineering",
      academic_year: "2026-27",
      status: "submitted",
      is_locked: true,
    },
    institution_id: 1,
    institution: {
      id: 1,
      aicte_id: "1-10000001",
      name: "Pune Institute of Advanced Engineering & Technology",
      state: "Maharashtra",
    },
    field: "status",
    old_value: "submitted",
    new_value: "withdrawn",
    reason: "Student cancelled admission and transferred to medical institute",
    status: "pending",
    decided_by: null,
    decided_by_email: null,
    decided_at: null,
    document_ref: "change_requests/inst_1/affidavit.pdf",
    decision_note: null,
    created_at: "2026-10-27T10:00:00Z",
    updated_at: "2026-10-27T10:00:00Z",
  },
  {
    id: 102,
    student_id: 502,
    student: {
      id: 502,
      apaar_id: "123456789013",
      name: "Sneha Kulkarni",
      course_id: 10,
      course_name: "Computer Engineering",
      academic_year: "2026-27",
      status: "submitted",
      is_locked: true,
    },
    institution_id: 1,
    institution: {
      id: 1,
      aicte_id: "1-10000001",
      name: "Pune Institute of Advanced Engineering & Technology",
      state: "Maharashtra",
    },
    field: "name",
    old_value: "Sneha Kulkarni",
    new_value: "Sneha M. Kulkarni",
    reason: "Name gazette notification spelling correction",
    status: "approved",
    decided_by: 2,
    decided_by_email: "officer@aicte-india.org",
    decided_at: "2026-10-27T12:00:00Z",
    document_ref: "change_requests/inst_1/gazette.pdf",
    decision_note: "Verified Gazette notification copy. Approved.",
    created_at: "2026-10-27T09:00:00Z",
    updated_at: "2026-10-27T12:00:00Z",
  },
];

describe("T26: Post-Lock Student Change Requests UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("CollegeChangeRequestsPage", () => {
    it("renders page header, KPI summary cards, and change requests table", async () => {
      vi.spyOn(changeRequestsApi, "getInstitutionChangeRequests").mockResolvedValue({
        items: mockChangeRequests,
        total: 2,
        limit: 50,
        offset: 0,
      });

      render(
        <BrowserRouter>
          <CollegeChangeRequestsPage />
        </BrowserRouter>
      );

      // Verify Header
      expect(screen.getByText("Post-Lock Change Requests")).toBeInTheDocument();

      // Wait for table to load
      await waitFor(() => {
        expect(screen.getByText("Rohan Patil")).toBeInTheDocument();
        expect(screen.getAllByText("Sneha Kulkarni").length).toBeGreaterThan(0);
      });

      // Verify table columns & values
      expect(screen.getByText("APAAR: 123456789012")).toBeInTheDocument();
      expect(screen.getByText("withdrawn")).toBeInTheDocument();
      expect(screen.getAllByText("Pending Review").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Approved").length).toBeGreaterThan(0);
      expect(screen.getByText("Verified Gazette notification copy. Approved.")).toBeInTheDocument();
    });

    it("opens submission modal and submits a new change request", async () => {
      vi.spyOn(changeRequestsApi, "getInstitutionChangeRequests").mockResolvedValue({
        items: mockChangeRequests,
        total: 2,
        limit: 50,
        offset: 0,
      });

      vi.spyOn(studentsApi, "getStudents").mockResolvedValue({
        items: [
          {
            id: 501,
            institution_id: 1,
            course_id: 10,
            course_name: "Computer Engineering",
            branch: "Computer Science",
            academic_year: "2026-27",
            apaar_id: "123456789012",
            name: "Rohan Patil",
            dob: "2004-01-01",
            gender: "Male",
            enrolment_no: "EN-001",
            admission_date: "2026-06-01",
            admission_mode: "State counselling",
            seat_type: "Regular",
            reservation_category: "General",
            nri: "No",
            oci: "No",
            foreign_national: "No",
            country: null,
            status: "submitted",
            is_locked: true,
            submission_id: 1,
            source: "form",
            flags: [],
            created_at: "2026-10-27T00:00:00Z",
            updated_at: "2026-10-27T00:00:00Z",
          },
        ],
        total: 1,
        page: 1,
        limit: 50,
        total_pages: 1,
        stats: {
          total: 1,
          valid: 1,
          flagged: 0,
          draft: 0,
          submitted: 1,
          error_flags_count: 0,
          exception_flags_count: 0,
          warning_flags_count: 0,
        },
      });

      const submitSpy = vi.spyOn(changeRequestsApi, "submitChangeRequest").mockResolvedValue({
        ...mockChangeRequests[0],
        id: 103,
      });

      render(
        <BrowserRouter>
          <CollegeChangeRequestsPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("New Change Request")).toBeInTheDocument();
      });

      // Click open modal
      fireEvent.click(screen.getByText("New Change Request"));

      await waitFor(() => {
        expect(screen.getByText("Submit Post-Lock Change Request")).toBeInTheDocument();
      });

      // Fill in reason
      const reasonInput = screen.getByPlaceholderText(
        /provide an official explanation/i
      );
      fireEvent.change(reasonInput, {
        target: { value: "Student formally submitted withdrawal letter." },
      });

      // Submit form
      const submitBtn = screen.getByText("Submit to AICTE");
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(submitSpy).toHaveBeenCalledWith(
          1,
          expect.objectContaining({
            student_id: 501,
            field: "status",
            new_value: "withdrawn",
            reason: "Student formally submitted withdrawal letter.",
          })
        );
      });
    });
  });

  describe("AicteChangeRequestsPage", () => {
    it("renders AICTE queue and allows approving a pending request", async () => {
      vi.spyOn(changeRequestsApi, "getAicteChangeRequests").mockResolvedValue({
        items: mockChangeRequests,
        total: 2,
        limit: 50,
        offset: 0,
      });

      const decideSpy = vi.spyOn(changeRequestsApi, "decideAicteChangeRequest").mockResolvedValue({
        ...mockChangeRequests[0],
        status: "approved",
      });

      render(
        <BrowserRouter>
          <AicteChangeRequestsPage />
        </BrowserRouter>
      );

      // Verify Header
      expect(screen.getByText("AICTE Student Change Requests Review")).toBeInTheDocument();

      // Wait for table to render
      await waitFor(() => {
        expect(screen.getAllByText(/Pune Institute of Advanced Engineering/i).length).toBeGreaterThan(0);
        expect(screen.getByText("Review & Decide")).toBeInTheDocument();
      });

      // Click "Review & Decide"
      fireEvent.click(screen.getByText("Review & Decide"));

      await waitFor(() => {
        expect(screen.getByText("Review Change Request #101")).toBeInTheDocument();
      });

      // Enter remarks
      const noteInput = screen.getByPlaceholderText(
        /enter verification remarks/i
      );
      fireEvent.change(noteInput, {
        target: { value: "Withdrawal letter verified. Approved." },
      });

      // Click Approve & Apply Change
      const approveBtn = screen.getByText("Approve & Apply Change");
      fireEvent.click(approveBtn);

      await waitFor(() => {
        expect(decideSpy).toHaveBeenCalledWith(101, {
          decision: "approve",
          decision_note: "Withdrawal letter verified. Approved.",
        });
      });
    });
  });
});
