import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import * as authModule from "../auth/AuthContext";
import * as seatsApi from "../api/seats";
import { SeatDeclarationsPage } from "../pages/SeatDeclarationsPage";

const mockCollegeAdmin = {
  id: 1,
  email: "admin@alpha-tech.edu.in",
  role: "college_admin" as const,
  institution_id: 101,
  is_active: true,
};

const mockSampleData: seatsApi.InstitutionSeatDeclarationResponse = {
  institution_id: 101,
  academic_year: "2026-27",
  total_approved_intake: 180,
  total_supernumerary_allowed: 18,
  total_declared_regular: 100,
  total_declared_supernumerary: 10,
  total_declared: 110,
  total_enrolled: 0,
  courses: [
    {
      course_id: 1,
      course_name: "Computer Science & Engineering",
      branch: "CSE",
      level: "UG",
      duration_years: 4,
      academic_year: "2026-27",
      approved_intake: 120,
      supernumerary_seats_allowed: 12,
      regular_admitted: 100,
      supernumerary_admitted: 10,
      nri_count: 5,
      oci_count: 0,
      fn_count: 0,
      total_declared: 110,
      calculated_enrolment: 0,
      calculated_regular: 0,
      calculated_supernumerary: 0,
      status: "draft",
      status_badge: "within_limit",
      overshoot: 0,
      supernumerary_overshoot: 0,
      flags: [],
      updated_at: new Date().toISOString(),
    },
    {
      course_id: 2,
      course_name: "Mechanical Engineering",
      branch: "MECH",
      level: "UG",
      duration_years: 4,
      academic_year: "2026-27",
      approved_intake: 60,
      supernumerary_seats_allowed: 6,
      regular_admitted: 0,
      supernumerary_admitted: 0,
      nri_count: 0,
      oci_count: 0,
      fn_count: 0,
      total_declared: 0,
      calculated_enrolment: 0,
      calculated_regular: 0,
      calculated_supernumerary: 0,
      status: "draft",
      status_badge: "within_limit",
      overshoot: 0,
      supernumerary_overshoot: 0,
      flags: [],
      updated_at: null,
    },
  ],
};

function setupAuth(role: "college_admin" | "college_staff" | "college_viewer" = "college_admin") {
  vi.spyOn(authModule, "useAuth").mockReturnValue({
    user: { ...mockCollegeAdmin, role },
    token: "mock.jwt.token",
    isAuthenticated: true,
    isLoading: false,
    pendingMfa: null,
    login: vi.fn(),
    verifyMfa: vi.fn(),
    cancelMfa: vi.fn(),
    logout: vi.fn(),
    hasRole: vi.fn(),
    isCollege: true,
    isAicte: false,
    isAdmin: role === "college_admin",
    refreshUser: vi.fn(),
  });
}

describe("T19: Seat Declarations Page UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(seatsApi, "saveCourseSeatDeclaration").mockImplementation(
      async (_instId, courseId, data) => {
        const base =
          mockSampleData.courses.find((c) => c.course_id === courseId) ||
          mockSampleData.courses[0];
        const reg = data.regular_admitted;
        const sup = data.supernumerary_admitted;
        const nri = data.nri_count || 0;
        const oci = data.oci_count || 0;
        const fn = data.fn_count || 0;
        const total = reg + sup;
        const catTotal = nri + oci + fn;

        const flags: seatsApi.ValidationFlagSummary[] = [];
        if (catTotal > total) {
          flags.push({
            rule_code: "SEAT_DECLARATION_INVALID",
            level: "error",
            message: `Total category admissions (${catTotal}) exceed total declared seats (${total}).`,
          });
        }
        if (reg > base.approved_intake) {
          flags.push({
            rule_code: "INTAKE_EXCEEDED",
            level: "exception",
            message: `Regular admitted students (${reg}) exceed approved intake (${base.approved_intake}) by ${reg - base.approved_intake}.`,
          });
        }

        return {
          ...base,
          regular_admitted: reg,
          supernumerary_admitted: sup,
          nri_count: nri,
          oci_count: oci,
          fn_count: fn,
          total_declared: total,
          status_badge: reg > base.approved_intake ? "over_by_n" : "within_limit",
          overshoot: Math.max(0, reg - base.approved_intake),
          flags,
        };
      }
    );
  });

  it("renders course summary table with approved quotas and lock indicator", async () => {
    setupAuth("college_admin");
    vi.spyOn(seatsApi, "getInstitutionSeatDeclarations").mockResolvedValue(mockSampleData);

    render(
      <BrowserRouter>
        <SeatDeclarationsPage />
      </BrowserRouter>
    );

    // Table renders
    await waitFor(() => {
      expect(screen.getByText("Seat Declarations & Course Summary")).toBeInTheDocument();
      expect(screen.getByText("Computer Science & Engineering")).toBeInTheDocument();
      expect(screen.getByText("Mechanical Engineering")).toBeInTheDocument();
    });

    // Approved quotas are displayed with lock indicator
    expect(screen.getByText("120")).toBeInTheDocument();
    expect(screen.getByText("180")).toBeInTheDocument(); // total approved
    expect(screen.getByText(/All courses within limits/i)).toBeInTheDocument();
  });

  it("performs live validation when input exceeds approved intake", async () => {
    setupAuth("college_admin");
    vi.spyOn(seatsApi, "getInstitutionSeatDeclarations").mockResolvedValue(mockSampleData);
    const saveMock = vi.spyOn(seatsApi, "saveCourseSeatDeclaration").mockResolvedValue({
      ...mockSampleData.courses[0],
      regular_admitted: 130,
      status_badge: "over_by_n",
      overshoot: 10,
      flags: [
        {
          rule_code: "INTAKE_EXCEEDED",
          level: "exception",
          message: "Regular admitted students (130) exceed approved intake (120) by 10.",
          fix_hint: "Submit justification.",
          field: "regular_admitted",
        },
      ],
    });

    render(
      <BrowserRouter>
        <SeatDeclarationsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Computer Science & Engineering")).toBeInTheDocument();
    });

    // Find the regular admitted input for the first course (value = 100)
    const inputs = screen.getAllByRole("spinbutton");
    const regularInput = inputs[0]; // first number input
    expect(regularInput).toHaveValue(100);

    // Change value to 130 (exceeds intake 120 by 10)
    fireEvent.change(regularInput, { target: { value: "130" } });

    // Live validation fires immediately: status changes to "Over by 10"
    await waitFor(() => {
      expect(screen.getByTestId("status-badge-over-1")).toHaveTextContent("Over by 10");
      expect(
        screen.getByText(/Regular admitted students \(130\) exceed approved intake \(120\) by 10/i)
      ).toBeInTheDocument();
    });

    // Debounced autosave triggers saveCourseSeatDeclaration
    await waitFor(
      () => {
        expect(saveMock).toHaveBeenCalledWith(101, 1, expect.objectContaining({
          regular_admitted: 130,
        }));
      },
      { timeout: 1500 }
    );
  });

  it("shows immediate error notice when category count exceeds declared seats", async () => {
    setupAuth("college_admin");
    vi.spyOn(seatsApi, "getInstitutionSeatDeclarations").mockResolvedValue(mockSampleData);

    render(
      <BrowserRouter>
        <SeatDeclarationsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Computer Science & Engineering")).toBeInTheDocument();
    });

    // Toggle expand button to show categories
    const expandButtons = screen.getAllByTitle(/Toggle Category Counts/i);
    fireEvent.click(expandButtons[0]);

    // Set NRI count to 500 (far exceeds total declared 110)
    const nriInput = screen.getByLabelText(/NRI Count:/i);
    fireEvent.change(nriInput, { target: { value: "500" } });

    // Live validation flag appears immediately (badge + detail hint)
    await waitFor(() => {
      expect(screen.getAllByText(/SEAT_DECLARATION_INVALID/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/exceed total declared seats/i)).toBeInTheDocument();
    });
  });

  it("disables inputs for college_viewer role", async () => {
    setupAuth("college_viewer");
    vi.spyOn(seatsApi, "getInstitutionSeatDeclarations").mockResolvedValue(mockSampleData);

    render(
      <BrowserRouter>
        <SeatDeclarationsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Computer Science & Engineering")).toBeInTheDocument();
    });

    const inputs = screen.getAllByRole("spinbutton");
    inputs.forEach((input) => {
      expect(input).toBeDisabled();
    });

    // Save draft button is not shown for viewers
    expect(screen.queryByRole("button", { name: /Save draft/i })).not.toBeInTheDocument();
  });
});
