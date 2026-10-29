import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AuthContext, type AuthContextType } from "../auth/AuthContext";
import { StudentsListPage } from "../pages/StudentsListPage";
import { StudentPortalPage } from "../pages/StudentPortalPage";
import * as verificationApi from "../api/verification";
import * as studentApi from "../api/students";
import * as institutionApi from "../api/institutions";

const mockCollegeAuth: AuthContextType = {
  user: {
    id: 1,
    email: "admin@piat-pune.edu.in",
    role: "college_admin",
    institution_id: 1,
    is_active: true,
  },
  token: "mock-college-token",
  isAuthenticated: true,
  isLoading: false,
  pendingMfa: null,
  login: vi.fn(),
  verifyMfa: vi.fn(),
  cancelMfa: vi.fn(),
  logout: vi.fn(),
  hasRole: vi.fn(() => true),
  isCollege: true,
  isAicte: false,
  isAdmin: true,
  refreshUser: vi.fn(),
};

function renderWithAuth(ui: React.ReactNode, authState: Partial<AuthContextType> = mockCollegeAuth) {
  const contextValue = { ...mockCollegeAuth, ...authState };
  return render(
    <AuthContext.Provider value={contextValue}>
      <MemoryRouter>{ui}</MemoryRouter>
    </AuthContext.Provider>
  );
}

describe("T35: Certificate PDF UI and Client Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Certificate API Helpers", () => {
    it("formats institutional certificate download URLs correctly", () => {
      const urlInline = verificationApi.getStudentCertificateUrl(1, 42, false);
      expect(urlInline).toBe("/api/v1/institutions/1/students/42/certificate");

      const urlDownload = verificationApi.getStudentCertificateUrl(1, 42, true);
      expect(urlDownload).toBe("/api/v1/institutions/1/students/42/certificate?download=true");
    });
  });

  describe("StudentsListPage Certificate Action", () => {
    it("renders Certificate button for each student and triggers download on click", async () => {
      vi.spyOn(institutionApi, "listCourses").mockResolvedValue([
        {
          id: 1,
          institution_id: 1,
          name: "Computer Science and Engineering",
          level: "UG",
          branch: "Computer Engineering",
          duration_years: 4,
          supernumerary_allowed: true,
          intakes: [],
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ]);

      vi.spyOn(studentApi, "getStudents").mockResolvedValue({
        items: [
          {
            id: 101,
            institution_id: 1,
            course_id: 1,
            academic_year: "2026-27",
            apaar_id: "987654321012",
            name: "Priya V. Kulkarni",
            dob: "2004-05-15",
            gender: "Female",
            enrolment_no: "PIAT-2026-042",
            admission_date: "2026-07-15",
            admission_mode: "State CET Quota",
            seat_type: "Regular",
            reservation_category: "General",
            nri: "No",
            oci: "No",
            foreign_national: "No",
            status: "verified",
            is_locked: true,
            source: "manual",
            course_name: "Computer Science and Engineering",
            branch: "Computer Engineering",
            flags: [],
            created_at: "2026-07-15T00:00:00Z",
            updated_at: "2026-07-15T00:00:00Z",
          },
        ],
        total: 1,
        page: 1,
        limit: 15,
        total_pages: 1,
        stats: {
          total: 1,
          draft: 0,
          submitted: 0,
          valid: 1,
          flagged: 0,
          error_flags_count: 0,
          exception_flags_count: 0,
          warning_flags_count: 0,
        },
      });

      const downloadSpy = vi
        .spyOn(verificationApi, "downloadStudentCertificate")
        .mockResolvedValue(undefined);

      renderWithAuth(<StudentsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Priya V. Kulkarni")).toBeInTheDocument();
      });

      const certButton = screen.getByRole("button", { name: /Certificate/i });
      expect(certButton).toBeInTheDocument();

      fireEvent.click(certButton);

      await waitFor(() => {
        expect(downloadSpy).toHaveBeenCalledWith(1, 101, "certificate_PIAT-2026-042.pdf");
      });
    });
  });

  describe("StudentPortalPage Certificate Action", () => {
    it("renders Certificate PDF button for enrolled records in student portal", async () => {
      // Mock session storage with active student token
      sessionStorage.setItem("apaar_student_token", "mock-student-session-jwt");
      sessionStorage.setItem("apaar_student_apaar", "987654321012");
      sessionStorage.setItem("apaar_student_name", "Priya Kulkarni");

      vi.spyOn(verificationApi, "getStudentAcademicRecords").mockResolvedValue({
        apaar_id: "987654321012",
        records: [
          {
            student_id: 101,
            enrolment_no: "PIAT-2026-042",
            institution_id: 1,
            institution_name: "Pune Institute of Advanced Technology",
            institution_aicte_id: "1-10000001",
            course_id: 1,
            course_name: "B.Tech Computer Engineering",
            academic_year: "2026-27",
            status: "verified",
            verification_id: "VR-2026-987654321012",
            issued_at: "2026-08-01T00:00:00Z",
          },
        ],
        total: 1,
      });

      vi.spyOn(verificationApi, "getStudentConsentRequests").mockResolvedValue({
        items: [],
        total: 0,
      });

      const downloadSpy = vi
        .spyOn(verificationApi, "downloadStudentPortalCertificate")
        .mockResolvedValue(undefined);

      renderWithAuth(<StudentPortalPage />);

      await waitFor(() => {
        expect(screen.getByText("Pune Institute of Advanced Technology")).toBeInTheDocument();
      });

      const certPdfBtn = screen.getByRole("button", { name: /Certificate PDF/i });
      expect(certPdfBtn).toBeInTheDocument();

      fireEvent.click(certPdfBtn);

      await waitFor(() => {
        expect(downloadSpy).toHaveBeenCalledWith(
          101,
          "mock-student-session-jwt",
          "certificate_PIAT-2026-042.pdf"
        );
      });

      sessionStorage.clear();
    });
  });
});
