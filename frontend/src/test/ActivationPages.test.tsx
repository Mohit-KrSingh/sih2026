import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { ActivatePage } from "../pages/ActivatePage";
import { AicteApprovalsPage } from "../pages/AicteApprovalsPage";
import { AicteIntakePage } from "../pages/AicteIntakePage";
import * as institutionsApi from "../api/institutions";

const renderWithAuth = (ui: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <AuthProvider>{ui}</AuthProvider>
    </BrowserRouter>,
  );
};

describe("T11: Activation Wizard, Approvals Queue & Intake Screens", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("ActivatePage Wizard", () => {
    it("renders step 1 lookup and transitions through OTP and claim submission", async () => {
      vi.spyOn(institutionsApi, "getActivationStatus").mockResolvedValue({
        aicte_id: "1-10000004",
        institution_name: "Bengaluru National Institute of Technology & Science",
        account_status: "not_activated",
        approval_status: "active",
        has_pending_request: false,
        latest_request_status: null,
        latest_request_id: null,
      });

      vi.spyOn(institutionsApi, "initiateActivation").mockResolvedValue({
        aicte_id: "1-10000004",
        institution_name: "Bengaluru National Institute of Technology & Science",
        masked_email: "d***r@bnits-blr.edu.in",
        masked_phone: "******1224",
        status: "pending_verification",
        message: "OTP sent to official contacts",
      });

      vi.spyOn(institutionsApi, "getDevOutbox").mockResolvedValue([
        {
          recipient: "d***r@bnits-blr.edu.in",
          channel: "email",
          body: "Your AICTE activation verification code is 654321.",
          created_at: new Date().toISOString(),
        },
      ]);

      vi.spyOn(institutionsApi, "verifyActivationOtp").mockResolvedValue({
        verified: true,
        activation_token: "jwt.activation.test.token",
        aicte_id: "1-10000004",
        institution_name: "Bengaluru National Institute of Technology & Science",
        head_name: "Dr. Ramesh Rao",
        message: "OTP verified successfully",
      });

      vi.spyOn(institutionsApi, "submitActivationMultipart").mockResolvedValue({
        id: 101,
        institution_id: 4,
        institution_aicte_id: "1-10000004",
        institution_name: "Bengaluru National Institute of Technology & Science",
        signatory_name: "Dr. Ramesh Rao",
        signatory_ref: "DL-REF-123456",
        letter_ref: "storage/letters/bnits_auth.pdf",
        status: "pending_approval",
        decided_by: null,
        decided_at: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      renderWithAuth(<ActivatePage />);

      // Step 1: Lookup
      const idInput = screen.getByLabelText(/AICTE Institute Identifier/i);
      fireEvent.change(idInput, { target: { value: "1-10000004" } });

      const verifyBtn = screen.getByRole("button", { name: "Verify institution" });
      fireEvent.click(verifyBtn);

      await waitFor(() => {
        expect(screen.getByText(/Institution Verified in AICTE Master Directory/i)).toBeInTheDocument();
      });

      // Send OTP
      const sendOtpBtn = screen.getByRole("button", { name: "Send OTP to official contact" });
      fireEvent.click(sendOtpBtn);

      // Step 2: OTP screen
      await waitFor(() => {
        expect(screen.getByText(/Step 2: Enter Verification Code/i)).toBeInTheDocument();
        expect(screen.getByText(/d\*\*\*r@bnits-blr\.edu\.in/)).toBeInTheDocument();
      });

      // Check OTP input & submit
      const otpInput = screen.getByLabelText(/6-Digit Verification Code/i);
      fireEvent.change(otpInput, { target: { value: "654321" } });

      const verifyOtpBtn = screen.getByRole("button", { name: "Verify OTP code" });
      fireEvent.click(verifyOtpBtn);

      // Step 3: Signatory & Letter screen
      await waitFor(() => {
        expect(screen.getByText(/Step 3: Authorized Signatory Verification/i)).toBeInTheDocument();
        expect(screen.getByDisplayValue("Dr. Ramesh Rao")).toBeInTheDocument();
      });

      // Attach mock letter file
      const fileInput = document.getElementById("letter-file-input") as HTMLInputElement;
      const testFile = new File(["dummy authorization letter content"], "bnits_auth_letter.pdf", {
        type: "application/pdf",
      });
      fireEvent.change(fileInput, { target: { files: [testFile] } });

      // Check agreement
      const agreeCb = screen.getByLabelText(/I solemnly declare/i);
      fireEvent.click(agreeCb);

      // Submit claim
      const submitBtn = screen.getByRole("button", { name: "Submit activation claim" });
      fireEvent.click(submitBtn);

      // Step 4: Confirmation screen
      await waitFor(() => {
        expect(screen.getByText("Activation Claim Successfully Submitted")).toBeInTheDocument();
        expect(screen.getByText("REQ-101")).toBeInTheDocument();
      });
    });

    it("checks status tab for existing institution claims", async () => {
      vi.spyOn(institutionsApi, "getActivationStatus").mockResolvedValue({
        aicte_id: "1-10000001",
        institution_name: "Pune Institute of Advanced Engineering & Technology",
        account_status: "active",
        approval_status: "active",
        has_pending_request: false,
        latest_request_status: "approved",
        latest_request_id: 1,
      });

      renderWithAuth(<ActivatePage />);

      const statusTabBtn = screen.getByRole("button", { name: "Check claim status" });
      fireEvent.click(statusTabBtn);

      expect(screen.getByText("Institution Claim Status Lookup")).toBeInTheDocument();

      const input = screen.getByLabelText(/AICTE Institute Identifier/i);
      fireEvent.change(input, { target: { value: "1-10000001" } });

      const checkBtn = screen.getByRole("button", { name: "Check status" });
      fireEvent.click(checkBtn);

      await waitFor(() => {
        expect(screen.getByText("Pune Institute of Advanced Engineering & Technology")).toBeInTheDocument();
        expect(screen.getByText("Account: active")).toBeInTheDocument();
        expect(screen.getByText("This institution account is active. You can log in with administrator credentials.")).toBeInTheDocument();
      });
    });
  });

  describe("AicteApprovalsPage Queue", () => {
    it("renders approval requests queue, displays details, and approves request", async () => {
      vi.spyOn(institutionsApi, "listActivationRequests").mockResolvedValue([
        {
          id: 42,
          institution_id: 4,
          institution_aicte_id: "1-10000004",
          institution_name: "Bengaluru National Institute of Technology & Science",
          signatory_name: "Dr. Ramesh Rao",
          signatory_ref: "DL-REF-998877",
          letter_ref: "storage/letters/bnits_auth.pdf",
          status: "pending_approval",
          decided_by: null,
          decided_at: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ]);

      vi.spyOn(institutionsApi, "approveActivation").mockResolvedValue({
        request_id: 42,
        institution_id: 4,
        status: "approved",
        institution_account_status: "active",
        admin_user_id: 10,
        admin_email: "admin@bnits-blr.edu.in",
        initial_password: "TempPassword!2026",
        mfa_enabled: true,
        mfa_secret: "JBSWY3DPEHPK3PXP",
        mfa_uri: "otpauth://totp/APAAR:admin@bnits-blr.edu.in?secret=JBSWY3DPEHPK3PXP",
        message: "Activation claim approved successfully",
      });

      renderWithAuth(<AicteApprovalsPage />);

      await waitFor(() => {
        expect(screen.getByText("Institution Approvals Queue")).toBeInTheDocument();
        expect(screen.getByText("Bengaluru National Institute of Technology & Science")).toBeInTheDocument();
        expect(screen.getByText("Pending Approval")).toBeInTheDocument();
      });

      // Click review
      const reviewBtn = screen.getByRole("button", { name: "Review claim" });
      fireEvent.click(reviewBtn);

      // Check modal open
      expect(screen.getByText("Institution Activation Review")).toBeInTheDocument();

      // Click approve claim in modal
      const approveActionBtn = screen.getByRole("button", { name: "Approve claim" });
      fireEvent.click(approveActionBtn);

      // Confirm approval
      const confirmApproveBtn = screen.getByRole("button", { name: "Confirm approval" });
      fireEvent.click(confirmApproveBtn);

      await waitFor(() => {
        expect(screen.getByText("Institution Claim Approved")).toBeInTheDocument();
        expect(screen.getByText("admin@bnits-blr.edu.in")).toBeInTheDocument();
        expect(screen.getByText("TempPassword!2026")).toBeInTheDocument();
      });
    });

    it("rejects an activation request with mandatory reason", async () => {
      vi.spyOn(institutionsApi, "listActivationRequests").mockResolvedValue([
        {
          id: 43,
          institution_id: 5,
          institution_aicte_id: "1-10000005",
          institution_name: "Chennai Technical College",
          signatory_name: "Dr. K. Swaminathan",
          signatory_ref: "DL-REF-554433",
          letter_ref: "storage/letters/chennai_auth.pdf",
          status: "pending_approval",
          decided_by: null,
          decided_at: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ]);

      const rejectSpy = vi.spyOn(institutionsApi, "rejectActivation").mockResolvedValue({
        request_id: 43,
        institution_id: 5,
        status: "rejected",
        institution_account_status: "not_activated",
        admin_user_id: null,
        admin_email: null,
        initial_password: null,
        mfa_enabled: false,
        mfa_secret: null,
        mfa_uri: null,
        message: "Activation claim rejected",
      });

      renderWithAuth(<AicteApprovalsPage />);

      await waitFor(() => {
        expect(screen.getByText("Chennai Technical College")).toBeInTheDocument();
      });

      const reviewBtn = screen.getByRole("button", { name: "Review claim" });
      fireEvent.click(reviewBtn);

      const rejectActionBtn = screen.getByRole("button", { name: "Reject claim" });
      fireEvent.click(rejectActionBtn);

      const reasonInput = screen.getByPlaceholderText(/Authorisation letter does not contain/i);
      fireEvent.change(reasonInput, {
        target: { value: "Authorisation letter is missing official stamp and signature" },
      });

      const confirmRejectBtn = screen.getByRole("button", { name: "Confirm rejection" });
      fireEvent.click(confirmRejectBtn);

      await waitFor(() => {
        expect(rejectSpy).toHaveBeenCalledWith(43, {
          reason: "Authorisation letter is missing official stamp and signature",
        });
      });
    });
  });

  describe("AicteIntakePage Quota & History", () => {
    it("displays approved courses, updates intake quota with audit reason, and views history", async () => {
      vi.spyOn(institutionsApi, "listInstitutions").mockResolvedValue({
        total: 1,
        items: [
          {
            id: 1,
            aicte_id: "1-10000001",
            name: "Pune Institute of Advanced Engineering & Technology",
            state: "Maharashtra",
            district: "Pune",
            address: "Survey 45, Katraj Bypass",
            official_email: "contact@piaet-pune.edu.in",
            official_phone: "9822011221",
            head_name: "Dr. Rajesh Deshmukh",
            affiliating_university: "SPPU",
            approval_status: "active",
            approval_valid_to: "2028-06-30",
            account_status: "active",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ],
      });

      vi.spyOn(institutionsApi, "listCourses").mockResolvedValue([
        {
          id: 10,
          institution_id: 1,
          name: "Computer Science and Engineering",
          level: "UG",
          branch: "Computer Science",
          duration_years: 4,
          supernumerary_allowed: true,
          intakes: [
            {
              id: 101,
              course_id: 10,
              academic_year: "2026-27",
              approved_intake: 180,
              supernumerary_seats_allowed: 9,
              source: "seed",
              set_by: "system",
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ]);

      const updateIntakeSpy = vi.spyOn(institutionsApi, "updateCourseIntake").mockResolvedValue({
        id: 101,
        course_id: 10,
        academic_year: "2026-27",
        approved_intake: 240,
        supernumerary_seats_allowed: 12,
        source: "officer",
        set_by: "officer@aicte-india.org",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      vi.spyOn(institutionsApi, "getIntakeHistory").mockResolvedValue([
        {
          id: 201,
          course_id: 10,
          academic_year: "2026-27",
          approved_intake: 180,
          supernumerary_seats_allowed: 9,
          source: "seed",
          set_by: "system",
          change_reason: "Initial baseline seed",
          created_at: new Date().toISOString(),
        },
      ]);

      renderWithAuth(<AicteIntakePage />);

      await waitFor(() => {
        expect(screen.getByText("AICTE Intake & Approval Control")).toBeInTheDocument();
        expect(screen.getByText("Computer Science and Engineering")).toBeInTheDocument();
        expect(screen.getByText("180")).toBeInTheDocument();
      });

      // Edit intake
      const editBtn = screen.getByRole("button", { name: "Edit intake" });
      fireEvent.click(editBtn);

      expect(screen.getByText(/Update Approved Intake: Computer Science/i)).toBeInTheDocument();

      const intakeInput = screen.getByLabelText(/Approved Regular Intake/i);
      fireEvent.change(intakeInput, { target: { value: "240" } });

      const supernumInput = screen.getByLabelText(/Supernumerary Allowed/i);
      fireEvent.change(supernumInput, { target: { value: "12" } });

      const reasonText = screen.getByPlaceholderText(/AICTE Approval Process Handbook/i);
      fireEvent.change(reasonText, {
        target: { value: "Approved additional division in AICTE Council Meeting 2026" },
      });

      const saveBtn = screen.getByRole("button", { name: "Save intake changes" });
      fireEvent.click(saveBtn);

      await waitFor(() => {
        expect(updateIntakeSpy).toHaveBeenCalledWith(1, 10, {
          academic_year: "2026-27",
          approved_intake: 240,
          supernumerary_seats_allowed: 12,
          change_reason: "Approved additional division in AICTE Council Meeting 2026",
        });
      });

      // View History
      const historyBtn = screen.getByRole("button", { name: "History" });
      fireEvent.click(historyBtn);

      await waitFor(() => {
        expect(screen.getByText("INTAKE HISTORY")).toBeInTheDocument();
        expect(screen.getByText("Initial baseline seed")).toBeInTheDocument();
      });
    });
  });
});
