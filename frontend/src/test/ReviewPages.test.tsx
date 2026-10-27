import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import * as authModule from "../auth/AuthContext";
import * as reviewApi from "../api/review";
import { AicteReviewPage } from "../pages/AicteReviewPage";
import { CollegeQueriesPage } from "../pages/CollegeQueriesPage";
import type {
  ReviewItemListResponse,
  ReviewItemDetailResponse,
  CollegeQueryListResponse,
} from "../types/review";

const mockAicteOfficer = {
  id: 101,
  email: "officer@aicte-india.org",
  role: "aicte_officer" as const,
  institution_id: null,
  is_active: true,
};

const mockCollegeAdmin = {
  id: 201,
  email: "admin@college.ac.in",
  role: "college_admin" as const,
  institution_id: 15,
  is_active: true,
};

function mockAuth(user: typeof mockAicteOfficer | typeof mockCollegeAdmin) {
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
    isCollege: user.role === "college_admin",
    isAicte: user.role === "aicte_officer",
    isAdmin: true,
    refreshUser: vi.fn(),
  });
}

const mockReviewItemsResponse: ReviewItemListResponse = {
  total: 2,
  pending_count: 1,
  under_review_count: 1,
  queries_raised_count: 0,
  escalated_count: 0,
  accepted_count: 0,
  items: [
    {
      id: 501,
      submission_id: 88,
      institution_id: 15,
      institution_name: "Maharashtra Institute of Technology",
      aicte_id: "1-10000002",
      state: "Maharashtra",
      academic_year: "2026-27",
      receipt_no: "REC-202627-1-10000002",
      status: "under_review",
      decision: null,
      decision_note: null,
      decided_at: null,
      assigned_to: 101,
      assigned_to_email: "officer@aicte-india.org",
      flag_ids: [901],
      rule_codes: ["INTAKE_EXCEEDED"],
      flag_count: 1,
      pending_queries_count: 0,
      created_at: "2026-09-20T10:00:00Z",
      updated_at: "2026-09-20T10:00:00Z",
    },
  ],
};

const mockItemDetailResponse: ReviewItemDetailResponse = {
  id: 501,
  submission_id: 88,
  institution_id: 15,
  institution_name: "Maharashtra Institute of Technology",
  aicte_id: "1-10000002",
  state: "Maharashtra",
  district: "Pune",
  academic_year: "2026-27",
  submission_status: "submitted_with_exceptions",
  receipt_no: "REC-202627-1-10000002",
  submitted_at: "2026-09-20T10:00:00Z",
  status: "under_review",
  decision: null,
  decision_note: null,
  decided_at: null,
  assigned_to: 101,
  assigned_to_email: "officer@aicte-india.org",
  flags: [
    {
      id: 901,
      submission_id: 88,
      rule_code: "INTAKE_EXCEEDED",
      level: "exception",
      field: "course_id",
      row_ref: "1",
      message: "Regular enrolment exceeds approved intake by 8 seats",
      fix_hint: "Verify court order or state admission allotment",
      status: "justified",
      student_id: 1001,
      student_name: "Aarav Patil",
      student_apaar: "XXXX-XXXX-1234",
      course_id: 201,
      course_name: "Computer Engineering",
      branch: "CSE",
      justifications: [
        {
          id: 301,
          flag_id: 901,
          text: "High Court interim order WP/2026/89 directed admission of 8 additional students.",
          document_ref: "storage/uploads/justifications/court_order.pdf",
          document_filename: "court_order.pdf",
          by_user_id: 201,
          by_user_email: "admin@college.ac.in",
          at: "2026-09-20T10:30:00Z",
        },
      ],
    },
  ],
  queries: [],
  created_at: "2026-09-20T10:00:00Z",
  updated_at: "2026-09-20T10:00:00Z",
};

const mockCollegeQueriesResponse: CollegeQueryListResponse = {
  total: 1,
  pending_count: 1,
  items: [
    {
      id: 401,
      review_item_id: 501,
      submission_id: 88,
      institution_id: 15,
      institution_name: "Maharashtra Institute of Technology",
      academic_year: "2026-27",
      receipt_no: "REC-202627-1-10000002",
      message: "Please provide the certified copy of page 4 of the High Court interim order.",
      response: null,
      state: "pending",
      created_at: "2026-09-21T09:00:00Z",
      responded_at: null,
      officer_name: "officer@aicte-india.org",
      flags: [
        {
          id: 901,
          submission_id: 88,
          rule_code: "INTAKE_EXCEEDED",
          level: "exception",
          message: "Regular enrolment exceeds approved intake by 8 seats",
          status: "open",
          student_id: 1001,
          student_name: "Aarav Patil",
          justifications: [],
        },
      ],
    },
  ],
};

describe("T25: AICTE Review Queue Page UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth(mockAicteOfficer);
    vi.spyOn(reviewApi, "fetchReviewItems").mockResolvedValue(mockReviewItemsResponse);
    vi.spyOn(reviewApi, "fetchReviewItemDetail").mockResolvedValue(mockItemDetailResponse);
    vi.spyOn(reviewApi, "submitReviewDecision").mockResolvedValue({
      ...mockItemDetailResponse,
      status: "accepted",
      decision: "accept",
      decision_note: "Court order WP/2026/89 verified and accepted.",
    });
  });

  it("renders queue header, summary KPI cards, and review queue table", async () => {
    render(
      <BrowserRouter>
        <AicteReviewPage />
      </BrowserRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "AICTE Submission Review Queue" }),
      ).toBeInTheDocument();
    });

    expect(screen.getByText("Total in Queue")).toBeInTheDocument();
    expect(screen.getByText("Maharashtra Institute of Technology")).toBeInTheDocument();
    expect(screen.getByText("1-10000002")).toBeInTheDocument();
    expect(screen.getByText("INTAKE_EXCEEDED")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Review Item" })).toBeInTheDocument();
  });

  it("opens review item detail modal, displays justifications and evidence download", async () => {
    render(
      <BrowserRouter>
        <AicteReviewPage />
      </BrowserRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Review Item" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Review Item" }));

    await waitFor(() => {
      expect(screen.getByText(/Aarav Patil/)).toBeInTheDocument();
      expect(screen.getByText(/High Court interim order WP\/2026\/89/)).toBeInTheDocument();
      expect(screen.getByText(/Download Document/)).toBeInTheDocument();
    });
  });

  it("submits an official review decision", async () => {
    render(
      <BrowserRouter>
        <AicteReviewPage />
      </BrowserRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Review Item" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Review Item" }));

    await waitFor(() => {
      expect(screen.getByText("Take Review Action")).toBeInTheDocument();
    });

    const noteInput = screen.getByPlaceholderText(/Verified court order/i);
    fireEvent.change(noteInput, {
      target: { value: "Court order WP/2026/89 verified and accepted." },
    });

    const submitBtn = screen.getByRole("button", {
      name: "Accept & Resolve Exceptions",
    });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(reviewApi.submitReviewDecision).toHaveBeenCalledWith(
        501,
        expect.objectContaining({
          decision: "accept",
          note: "Court order WP/2026/89 verified and accepted.",
        }),
      );
    });
  });
});

describe("T25: College Clarification Queries Page UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth(mockCollegeAdmin);
    vi.spyOn(reviewApi, "fetchCollegeQueries").mockResolvedValue(mockCollegeQueriesResponse);
    vi.spyOn(reviewApi, "respondToCollegeQuery").mockResolvedValue({
      ...mockCollegeQueriesResponse.items[0],
      state: "answered",
      response: "Certified copy of page 4 attached showing bench approval.",
    });
  });

  it("renders clarification queries list with pending inquiry from AICTE", async () => {
    render(
      <BrowserRouter>
        <CollegeQueriesPage />
      </BrowserRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "AICTE Clarification Queries" }),
      ).toBeInTheDocument();
    });

    expect(screen.getByText(/Please provide the certified copy of page 4/)).toBeInTheDocument();
    expect(screen.getByText("Pending Your Response")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Respond to Inquiry" })).toBeInTheDocument();
  });

  it("allows college staff to open response form and submit clarification", async () => {
    render(
      <BrowserRouter>
        <CollegeQueriesPage />
      </BrowserRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Respond to Inquiry" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Respond to Inquiry" }));

    await waitFor(() => {
      expect(screen.getByText("Submit Official College Clarification")).toBeInTheDocument();
    });

    const responseInput = screen.getByPlaceholderText(/Provide clear legal, statutory/i);
    fireEvent.change(responseInput, {
      target: { value: "Certified copy of page 4 attached showing bench approval." },
    });

    const submitBtn = screen.getByRole("button", { name: "Submit Response to AICTE" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(reviewApi.respondToCollegeQuery).toHaveBeenCalledWith(
        15,
        401,
        expect.objectContaining({
          response: "Certified copy of page 4 attached showing bench approval.",
        }),
      );
    });
  });
});
