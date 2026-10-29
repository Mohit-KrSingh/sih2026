import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { AicteOverviewPage } from "../pages/AicteOverviewPage";
import { AicteCompliancePage } from "../pages/AicteCompliancePage";
import { AicteDuplicatesPage } from "../pages/AicteDuplicatesPage";
import { AicteAnomaliesPage } from "../pages/AicteAnomaliesPage";
import { AicteDrilldownPage } from "../pages/AicteDrilldownPage";
import { AicteRulesPage } from "../pages/AicteRulesPage";
import { AicteAuditPage } from "../pages/AicteAuditPage";
import * as analyticsApi from "../api/analytics";
import * as rulesApi from "../api/rules";
import * as auditApi from "../api/audit";

// Mock echarts-for-react to cleanly render in jsdom
vi.mock("echarts-for-react", () => ({
  default: (props: any) => {
    const domProps = { ...props };
    delete domProps.notMerge;
    delete domProps.lazyUpdate;
    return <div data-testid="echarts-mock" {...domProps} />;
  },
}));

// Mock AuthContext
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: 99,
      email: "aicte_admin@aicte-india.org",
      role: "aicte_admin",
      institution_id: null,
    },
    token: "mock-token",
    isAuthenticated: true,
  }),
}));

describe("AICTE Dashboard & Oversight Pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders AicteOverviewPage with KPIs, prominent Red List, and live feed", async () => {
    vi.spyOn(analyticsApi, "getOverviewMetrics").mockResolvedValue({
      academic_year: "2026-27",
      total_colleges: 30,
      active_colleges: 20,
      pending_activation_colleges: 5,
      total_students_enrolled: 4500,
      total_approved_intake: 5000,
      total_supernumerary_intake: 300,
      total_courses: 45,
      total_errors: 12,
      total_exceptions: 3,
      total_warnings: 8,
      total_infos: 2,
      total_duplicate_cases: 1,
      total_anomalies_flagged: 2,
      over_intake_violations_count: 1,
      submission_progress: {
        submitted_clean: 10,
        submitted_with_exceptions: 2,
        under_review: 2,
        accepted: 8,
        query_raised: 1,
        escalated: 0,
        draft: 4,
        not_started: 3,
        total_eligible: 30,
      },
    });

    vi.spyOn(analyticsApi, "getComplianceList").mockResolvedValue({
      academic_year: "2026-27",
      total_violations: 1,
      red_list_colleges_count: 1,
      violations: [
        {
          institution_id: 1,
          aicte_id: "1-10000001",
          institution_name: "Pune Institute of Advanced Engineering & Technology",
          state: "Maharashtra",
          course_id: 10,
          course_name: "Computer Science and Engineering",
          level: "UG",
          approved_intake: 60,
          regular_admitted: 70,
          overshoot: 10,
          supernumerary_allowed: 6,
          supernumerary_admitted: 4,
          is_red_list: true,
          submission_status: "submitted_with_exceptions",
          last_updated: "2026-10-27T10:00:00Z",
        },
      ],
    });

    vi.spyOn(analyticsApi, "getStateMetrics").mockResolvedValue({
      academic_year: "2026-27",
      total_states: 1,
      items: [
        {
          state: "Maharashtra",
          colleges_count: 8,
          approved_intake: 1200,
          regular_admitted: 1100,
          supernumerary_admitted: 80,
          total_enrolled: 1180,
          utilization_rate: 98.3,
          over_intake_colleges: 1,
          exceptions_count: 2,
          duplicates_count: 1,
          submissions_completed: 6,
        },
      ],
    });

    vi.spyOn(analyticsApi, "getCourseMetrics").mockResolvedValue({
      academic_year: "2026-27",
      total_disciplines: 1,
      items: [
        {
          course_name: "Computer Science and Engineering",
          level: "UG",
          total_courses: 15,
          colleges_count: 12,
          approved_intake: 1800,
          regular_admitted: 1750,
          supernumerary_admitted: 120,
          total_enrolled: 1870,
          utilization_rate: 103.8,
          over_intake_violations: 1,
        },
      ],
    });

    vi.spyOn(analyticsApi, "getRecentEvents").mockResolvedValue([
      {
        id: "evt-1",
        event: "flag_detected",
        data: { message: "INTAKE_EXCEEDED flagged for Pune Institute" },
        timestamp: "2026-10-27T10:30:00Z",
      },
    ]);

    render(
      <BrowserRouter>
        <AicteOverviewPage />
      </BrowserRouter>
    );

    // Verify main header
    await waitFor(() => {
      expect(
        screen.getByText("Central Oversight & Analytics Dashboard")
      ).toBeInTheDocument();
    });

    // Verify KPIs
    expect(screen.getByText("4,500")).toBeInTheDocument();
    expect(screen.getByText("5,000")).toBeInTheDocument();

    // Verify prominent Over-Intake Red List
    expect(
      screen.getByText("Over-Intake Compliance Red List")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Pune Institute of Advanced Engineering & Technology")
    ).toBeInTheDocument();
    expect(screen.getByText("+10 Over Intake")).toBeInTheDocument();

    // Verify Live Feed and SSE status chip
    expect(screen.getByText("Live System Activity Feed")).toBeInTheDocument();
    expect(screen.getByText("CONNECTED")).toBeInTheDocument();
    expect(screen.getByTestId("sse-status-chip")).toHaveTextContent("Live");

    // Verify ECharts containers are rendered
    expect(screen.getAllByTestId("echarts-mock").length).toBeGreaterThanOrEqual(1);

    // Verify AccessibleChartCard "View as table" toggle and accessible tables
    const viewAsTableButtons = screen.getAllByRole("button", { name: /view as table/i });
    expect(viewAsTableButtons.length).toBe(3);

    // Toggle the first chart (State Intake) to table view
    fireEvent.click(viewAsTableButtons[0]);
    expect(screen.getByRole("button", { name: /view as chart for State-Level Intake vs Actual Enrolment/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /State-Level Intake vs Actual Enrolment data table/i })).toBeInTheDocument();

    // Toggle back to chart view
    fireEvent.click(screen.getByRole("button", { name: /view as chart for State-Level Intake vs Actual Enrolment/i }));
    expect(screen.getAllByRole("button", { name: /view as table/i }).length).toBe(3);
  });

  it("renders AicteCompliancePage with over-intake filters and notice trigger", async () => {
    vi.spyOn(analyticsApi, "getComplianceList").mockResolvedValue({
      academic_year: "2026-27",
      total_violations: 1,
      red_list_colleges_count: 1,
      violations: [
        {
          institution_id: 2,
          aicte_id: "1-10000002",
          institution_name: "Mumbai Metropolitan Institute of Technology",
          state: "Maharashtra",
          course_id: 20,
          course_name: "Mechanical Engineering",
          level: "UG",
          approved_intake: 120,
          regular_admitted: 135,
          overshoot: 15,
          supernumerary_allowed: 12,
          supernumerary_admitted: 8,
          is_red_list: true,
          submission_status: "submitted_with_exceptions",
          last_updated: "2026-10-27T11:00:00Z",
        },
      ],
    });

    render(
      <BrowserRouter>
        <AicteCompliancePage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText("Over-Intake Compliance & Red List")
      ).toBeInTheDocument();
    });

    expect(
      screen.getByText("Mumbai Metropolitan Institute of Technology")
    ).toBeInTheDocument();
    expect(screen.getByText("+15 Overshoot")).toBeInTheDocument();

    // Click issue notice button and check modal opens
    const issueNoticeBtn = screen.getByRole("button", { name: /issue notice/i });
    fireEvent.click(issueNoticeBtn);

    expect(screen.getByText("Dispatch Official Notice")).toBeInTheDocument();
    expect(screen.getByText("Notice Urgency Level")).toBeInTheDocument();
  });

  it("renders AicteDuplicatesPage with cross-college duplicate pairs", async () => {
    vi.spyOn(analyticsApi, "getDuplicates").mockResolvedValue({
      total_duplicates: 1,
      items: [
        {
          apaar_id: "555566667777",
          student_name: "Vikram Malhotra",
          academic_year: "2026-27",
          rule_code: "DUP_ACTIVE_OTHER_COLLEGE",
          level: "warning",
          status: "open",
          colleges: [
            {
              institution_id: 1,
              institution_name: "Pune Institute",
              aicte_id: "1-10000001",
              course_name: "Computer Science",
              status: "submitted",
            },
            {
              institution_id: 2,
              institution_name: "Mumbai Institute",
              aicte_id: "1-10000002",
              course_name: "Computer Engineering",
              status: "draft",
            },
          ],
        },
      ],
    });

    render(
      <BrowserRouter>
        <AicteDuplicatesPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText("Cross-College Duplicate Enrolments")
      ).toBeInTheDocument();
    });

    expect(screen.getByText("Vikram Malhotra")).toBeInTheDocument();
    expect(screen.getByText("APAAR: 555566667777")).toBeInTheDocument();
    expect(screen.getByText("Pune Institute")).toBeInTheDocument();
    expect(screen.getByText("Mumbai Institute")).toBeInTheDocument();
  });

  it("renders AicteAnomaliesPage with IsolationForest score and plain-English explanation", async () => {
    vi.spyOn(analyticsApi, "getAnomalies").mockResolvedValue({
      total: 1,
      flagged_count: 1,
      items: [
        {
          id: 50,
          institution_id: 1,
          institution_name: "Pune Institute",
          aicte_id: "1-10000001",
          course_id: 10,
          course_name: "Computer Science",
          academic_year: "2026-27",
          score: -0.2154,
          flagged: true,
          summary: "Unusual YoY enrolment surge of +33.3% and 12 sequential APAAR IDs detected",
          features: {
            yoy_growth: 0.333,
            nri_share: 0.12,
            supernum_share: 0.08,
            dob_cluster_ratio: 0.05,
            admission_day_concentration: 0.45,
            max_apaar_sequence_run: 12,
          },
          created_at: "2026-10-27T12:00:00Z",
        },
      ],
    });

    render(
      <BrowserRouter>
        <AicteAnomaliesPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText("Intelligent Anomaly Detection & Pattern Recognition")
      ).toBeInTheDocument();
    });

    expect(screen.getByText("Flagged Anomaly")).toBeInTheDocument();
    expect(
      screen.getByText(/Unusual YoY enrolment surge of \+33\.3%/i)
    ).toBeInTheDocument();
    expect(screen.getByText("33.3%")).toBeInTheDocument();
    expect(screen.getByText("12 IDs")).toBeInTheDocument();
  });

  it("renders AicteDrilldownPage with interactive hierarchy", async () => {
    vi.spyOn(analyticsApi, "getDrilldown").mockResolvedValue({
      academic_year: "2026-27",
      level: "national",
      state: null,
      institution: null,
      course: null,
      states: [
        {
          state: "Maharashtra",
          colleges_count: 8,
          total_enrolled: 1100,
          approved_intake: 1200,
          overshoot: 10,
          over_intake_colleges: 1,
        },
        {
          state: "Karnataka",
          colleges_count: 5,
          total_enrolled: 700,
          approved_intake: 750,
          overshoot: 0,
          over_intake_colleges: 0,
        },
      ],
      colleges: [],
      courses: [],
      students: [],
    });

    render(
      <BrowserRouter>
        <AicteDrilldownPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText("Institutional Data Explorer & Student Auditing")
      ).toBeInTheDocument();
    });

    expect(screen.getByText("All States (National)")).toBeInTheDocument();
    expect(screen.getByText("Maharashtra")).toBeInTheDocument();
    expect(screen.getByText("Karnataka")).toBeInTheDocument();
  });

  it("renders AicteRulesPage with rule catalogue and admin configure modal", async () => {
    vi.spyOn(rulesApi, "getRules").mockResolvedValue({
      total: 34,
      overridden_count: 1,
      items: [
        {
          rule_code: "INTAKE_EXCEEDED",
          scope: "course",
          default_level: "exception",
          current_level: "exception",
          meaning: "Regular admitted is above approved intake",
          default_params: {},
          current_params: {},
          enabled: true,
          is_overridden: false,
          updated_by: null,
          updated_at: null,
        },
        {
          rule_code: "ANOM_ENROLMENT_JUMP",
          scope: "anomaly",
          default_level: "warning",
          current_level: "error",
          meaning: "Enrolment up more than threshold",
          default_params: { threshold_percent: 30.0 },
          current_params: { threshold_percent: 45.0 },
          enabled: true,
          is_overridden: true,
          updated_by: 99,
          updated_at: "2026-10-27T14:00:00Z",
        },
      ],
    });

    render(
      <BrowserRouter>
        <AicteRulesPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText("Validation Rules & Policy Customization")
      ).toBeInTheDocument();
    });

    expect(screen.getByText("INTAKE_EXCEEDED")).toBeInTheDocument();
    expect(screen.getByText("ANOM_ENROLMENT_JUMP")).toBeInTheDocument();
    expect(screen.getByText("Custom")).toBeInTheDocument();

    // Click configure button
    const configureBtns = screen.getAllByRole("button", { name: /configure/i });
    fireEvent.click(configureBtns[0]);

    expect(screen.getByText(/Configure Policy:/i)).toBeInTheDocument();
    expect(screen.getByText("Override Validation Level")).toBeInTheDocument();
  });

  it("renders AicteAuditPage with hash chain verification button", async () => {
    vi.spyOn(auditApi, "getAuditLogs").mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          ts: "2026-10-27T15:00:00Z",
          actor_id: "99",
          actor_role: "aicte_admin",
          action: "rule_config.update",
          entity: "rule_config",
          entity_id: "5",
          before_json: { level: "warning" },
          after_json: { level: "error" },
          ip: "127.0.0.1",
          prev_hash: "00000000000000000000000000000000",
          hash: "abc123def4567890abcdef1234567890abcdef1234567890abcdef1234567890",
        },
      ],
      limit: 25,
      offset: 0,
    });

    vi.spyOn(auditApi, "verifyAuditChain").mockResolvedValue({
      verified: true,
      total_records: 1,
      first_broken_id: null,
      broken_index: null,
      reason: null,
    });

    render(
      <BrowserRouter>
        <AicteAuditPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText("Hash-Chained Audit Trail & Tamper Verification")
      ).toBeInTheDocument();
    });

    expect(screen.getByText("rule_config.update")).toBeInTheDocument();

    // Click verify chain integrity
    const verifyBtn = screen.getByRole("button", { name: /verify chain integrity/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(
        screen.getByText("Cryptographic SHA-256 Hash Chain Verified Intact")
      ).toBeInTheDocument();
    });
  });
});
