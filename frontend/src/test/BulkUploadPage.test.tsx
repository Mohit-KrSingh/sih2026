import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import * as authModule from "../auth/AuthContext";
import * as studentsApi from "../api/students";
import * as institutionsApi from "../api/institutions";
import { BulkUploadPage } from "../pages/BulkUploadPage";

const mockUser = {
  id: 1,
  email: "admin@college.edu",
  role: "college_admin" as const,
  institution_id: 10,
  is_active: true,
};

const mockCourses: institutionsApi.CourseResponse[] = [
  {
    id: 101,
    institution_id: 10,
    name: "Computer Science and Engineering",
    branch: "Computer Science",
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
    branch: "Mechanical",
    level: "UG",
    duration_years: 4,
    supernumerary_allowed: false,
    intakes: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

const mockUploadResult: studentsApi.UploadResultResponse = {
  upload_id: 55,
  filename: "messy_upload.csv",
  row_count: 3,
  summary: {
    total_rows: 3,
    valid_rows: 1,
    flagged_rows: 2,
    error_count: 2,
    exception_count: 0,
    warning_count: 1,
    info_count: 0,
    inserted_count: 3,
    updated_count: 0,
  },
  rows: [
    {
      row_number: 1,
      student_id: 501,
      apaar_id: "900011112222",
      name: "Amit Verma",
      dob: "2004-05-10",
      gender: "Male",
      course: "Computer Science and Engineering",
      branch: "Computer Science",
      admission_year: "2026-27",
      enrolment_no: "ENR-001",
      admission_date: "2026-07-15",
      admission_mode: "State counselling",
      seat_type: "Regular",
      reservation_category: "General",
      nri: "No",
      oci: "No",
      foreign_national: "No",
      country: null,
      status: "valid",
      flags: [],
    },
    {
      row_number: 2,
      student_id: 502,
      apaar_id: "12345678901",
      name: "Rohan Joshi",
      dob: "2004-05-10",
      gender: "Male",
      course: "Computer Science and Engineering",
      branch: "Computer Science",
      admission_year: "2026-27",
      enrolment_no: "ENR-002",
      admission_date: "2026-07-15",
      admission_mode: "State counselling",
      seat_type: "Regular",
      reservation_category: "General",
      nri: "No",
      oci: "No",
      foreign_national: "No",
      country: null,
      status: "flagged",
      flags: [
        {
          rule_code: "APAAR_FORMAT",
          level: "error",
          field: "apaar_id",
          message: "APAAR ID '12345678901' is invalid. It must be exactly 12 numeric digits.",
          fix_hint: "Check and provide valid 12-digit APAAR ID.",
          requires_justification: false,
          status: "open",
        },
      ],
    },
    {
      row_number: 3,
      student_id: 503,
      apaar_id: "900033334444",
      name: "Suresh Raina",
      dob: "2004-05-10",
      gender: "Male",
      course: "Astrophysics & Space Flight",
      branch: "Aerospace",
      admission_year: "2026-27",
      enrolment_no: "ENR-003",
      admission_date: "2026-07-15",
      admission_mode: "State counselling",
      seat_type: "Regular",
      reservation_category: "General",
      nri: "No",
      oci: "No",
      foreign_national: "No",
      country: null,
      status: "flagged",
      flags: [
        {
          rule_code: "COURSE_NOT_APPROVED",
          level: "error",
          field: "course",
          message: "Course 'Astrophysics & Space Flight' is not approved for this institution.",
          fix_hint: "Select an approved course from the curriculum list.",
          requires_justification: false,
          status: "open",
        },
        {
          rule_code: "ADMISSION_DATE_WINDOW",
          level: "warning",
          field: "admission_date",
          message: "Admission date outside standard window.",
          fix_hint: "Adjust admission date if typed incorrectly.",
          requires_justification: false,
          status: "open",
        },
      ],
    },
  ],
};

const mockUploadHistory: studentsApi.UploadHistoryResponse = {
  items: [
    {
      id: 55,
      institution_id: 10,
      filename: "messy_upload.csv",
      row_count: 3,
      status: "completed",
      summary_json: {
        summary: mockUploadResult.summary,
      },
      uploaded_by: 1,
      created_at: "2026-10-27T10:00:00Z",
    },
  ],
  total: 1,
};

describe("BulkUploadPage UI Component", () => {
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

    vi.spyOn(institutionsApi, "listCourses").mockResolvedValue(mockCourses);
    vi.spyOn(studentsApi, "downloadTemplateCsv").mockResolvedValue("apaar_id,name,dob\n");
    vi.spyOn(studentsApi, "uploadStudentsFile").mockResolvedValue(mockUploadResult);
    vi.spyOn(studentsApi, "getUploadHistory").mockResolvedValue(mockUploadHistory);
    vi.spyOn(studentsApi, "getUploadDetails").mockResolvedValue(mockUploadResult);
    vi.spyOn(studentsApi, "downloadErrorCsv").mockResolvedValue(
      "row_number,field,rule_code,level,message,fix_hint\n2,apaar_id,APAAR_FORMAT,error,Invalid,Fix it\n"
    );
  });

  it("renders upload form, academic year selector, and template download button", async () => {
    render(
      <BrowserRouter>
        <BulkUploadPage />
      </BrowserRouter>
    );

    expect(screen.getByText("Bulk Student Enrolment Upload")).toBeInTheDocument();
    expect(screen.getByText("Download CSV Template")).toBeInTheDocument();
    expect(screen.getByText(/Target Academic Year/i)).toBeInTheDocument();
    expect(screen.getByText(/Upload & Run Validation Engine/i)).toBeInTheDocument();
  });

  it("triggers template CSV download", async () => {
    render(
      <BrowserRouter>
        <BulkUploadPage />
      </BrowserRouter>
    );

    const downloadBtn = screen.getByText("Download CSV Template");
    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(studentsApi.downloadTemplateCsv).toHaveBeenCalledWith(10);
    });
  });

  it("uploads file and transitions to results screen with counts and rows", async () => {
    render(
      <BrowserRouter>
        <BulkUploadPage />
      </BrowserRouter>
    );

    // Provide a file
    const file = new File(["dummy content"], "messy_upload.csv", { type: "text/csv" });
    const fileInput = document.getElementById("file-upload") as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Click upload
    const uploadBtn = screen.getByText(/Upload & Run Validation Engine/i);
    fireEvent.click(uploadBtn);

    await waitFor(() => {
      expect(studentsApi.uploadStudentsFile).toHaveBeenCalledWith(10, file, "2026-27");
    });

    // Verify Results tab is now active and summary cards render
    await waitFor(() => {
      expect(screen.getByText("Upload Results (3 rows)")).toBeInTheDocument();
      expect(screen.getByText("Valid (Clean)")).toBeInTheDocument();
      expect(screen.getByText("Flagged Rows")).toBeInTheDocument();
    });

    // Check student names in table
    expect(screen.getByText("Amit Verma")).toBeInTheDocument();
    expect(screen.getByText("Rohan Joshi")).toBeInTheDocument();
    expect(screen.getByText("Suresh Raina")).toBeInTheDocument();
  });

  it("expands row to view flag messages and fix hints", async () => {
    render(
      <BrowserRouter>
        <BulkUploadPage />
      </BrowserRouter>
    );

    const file = new File(["dummy"], "test.csv", { type: "text/csv" });
    const fileInput = document.getElementById("file-upload") as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.click(screen.getByText(/Upload & Run Validation Engine/i));

    await waitFor(() => {
      expect(screen.getByText("Rohan Joshi")).toBeInTheDocument();
    });

    // Click Details button on Row 2
    const detailsButtons = screen.getAllByText("Details");
    fireEvent.click(detailsButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("APAAR_FORMAT")).toBeInTheDocument();
      expect(
        screen.getByText(/APAAR ID '12345678901' is invalid\. It must be exactly 12 numeric digits\./i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Check and provide valid 12-digit APAAR ID\./i)).toBeInTheDocument();
    });
  });

  it("filters rows by flag level", async () => {
    render(
      <BrowserRouter>
        <BulkUploadPage />
      </BrowserRouter>
    );

    const file = new File(["dummy"], "test.csv", { type: "text/csv" });
    const fileInput = document.getElementById("file-upload") as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.click(screen.getByText(/Upload & Run Validation Engine/i));

    await waitFor(() => {
      expect(screen.getByText("Amit Verma")).toBeInTheDocument();
    });

    // Select "Clean / Valid Only"
    const levelSelect = screen.getByDisplayValue("All Flag Levels");
    fireEvent.change(levelSelect, { target: { value: "clean" } });

    // Only Amit Verma should remain
    expect(screen.getByText("Amit Verma")).toBeInTheDocument();
    expect(screen.queryByText("Rohan Joshi")).not.toBeInTheDocument();
  });

  it("performs inline edit and saves updated student row", async () => {
    vi.spyOn(studentsApi, "updateStudent").mockResolvedValue({
      student: {
        id: 502,
        institution_id: 10,
        course_id: 101,
        course_name: "Computer Science and Engineering",
        branch: "Computer Science",
        academic_year: "2026-27",
        apaar_id: "12345678901",
        name: "Rohan Joshi Updated",
        dob: "2004-05-10",
        gender: "Male",
        enrolment_no: "ENR-002",
        admission_date: "2026-07-15",
        admission_mode: "State counselling",
        seat_type: "Regular",
        reservation_category: "General",
        nri: "No",
        oci: "No",
        foreign_national: "No",
        country: null,
        status: "valid",
        is_locked: false,
        source: "csv",
        flags: [],
        created_at: "2026-10-27T10:00:00Z",
        updated_at: "2026-10-27T10:05:00Z",
      },
      flags: [],
      is_valid: true,
      errors_count: 0,
      exceptions_count: 0,
      warnings_count: 0,
      infos_count: 0,
    });

    render(
      <BrowserRouter>
        <BulkUploadPage />
      </BrowserRouter>
    );

    const file = new File(["dummy"], "test.csv", { type: "text/csv" });
    const fileInput = document.getElementById("file-upload") as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.click(screen.getByText(/Upload & Run Validation Engine/i));

    await waitFor(() => {
      expect(screen.getByText("Rohan Joshi")).toBeInTheDocument();
    });

    // Click Inline Edit for Row 2
    const editButtons = screen.getAllByText("Inline Edit");
    fireEvent.click(editButtons[1]); // Row 2

    // Change name in inline input
    const nameInput = screen.getByDisplayValue("Rohan Joshi");
    fireEvent.change(nameInput, { target: { value: "Rohan Joshi Updated" } });

    // Click Save & Re-validate
    const saveBtn = screen.getByText("Save & Re-validate");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(studentsApi.updateStudent).toHaveBeenCalled();
      expect(screen.getByText("Rohan Joshi Updated")).toBeInTheDocument();
      expect(screen.getByText(/Row #2 updated and re-validated successfully/i)).toBeInTheDocument();
    });
  });

  it("navigates to Upload History and allows viewing previous uploads", async () => {
    render(
      <BrowserRouter>
        <BulkUploadPage />
      </BrowserRouter>
    );

    const historyTab = screen.getByText("Upload History");
    fireEvent.click(historyTab);

    await waitFor(() => {
      expect(studentsApi.getUploadHistory).toHaveBeenCalledWith(10);
      expect(screen.getByText("Historical Bulk Uploads")).toBeInTheDocument();
      expect(screen.getByText("messy_upload.csv")).toBeInTheDocument();
    });

    // Click View Results on history row
    const viewResultsBtn = screen.getByText("View Results");
    fireEvent.click(viewResultsBtn);

    await waitFor(() => {
      expect(studentsApi.getUploadDetails).toHaveBeenCalledWith(10, 55);
      expect(screen.getByText("Upload Results (3 rows)")).toBeInTheDocument();
    });
  });
});
