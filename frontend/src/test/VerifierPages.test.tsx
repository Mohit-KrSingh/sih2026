import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextType } from "../auth/AuthContext";
import { VerifierSearchPage } from "../pages/VerifierSearchPage";
import { VerifierHistoryPage } from "../pages/VerifierHistoryPage";
import { VerifyPage } from "../pages/VerifyPage";
import { StudentPortalPage } from "../pages/StudentPortalPage";

const mockVerifierAuth: AuthContextType = {
  user: {
    id: 10,
    email: "verifier@tcs-verifications.com",
    role: "verifier",
    institution_id: null,
    is_active: true,
  },
  token: "mock-verifier-token",
  isAuthenticated: true,
  isLoading: false,
  pendingMfa: null,
  login: vi.fn(),
  verifyMfa: vi.fn(),
  cancelMfa: vi.fn(),
  logout: vi.fn(),
  hasRole: vi.fn((role) => (Array.isArray(role) ? role.includes("verifier") : role === "verifier")),
  isCollege: false,
  isAicte: false,
  isAdmin: false,
  refreshUser: vi.fn(),
};

function renderWithAuth(ui: React.ReactNode, authState: Partial<AuthContextType> = mockVerifierAuth) {
  const contextValue = { ...mockVerifierAuth, ...authState };
  return render(
    <AuthContext.Provider value={contextValue}>
      <MemoryRouter>{ui}</MemoryRouter>
    </AuthContext.Provider>
  );
}

describe("T34: Verification Portal and Student Consent UI", () => {
  describe("VerifierSearchPage", () => {
    it("renders verifier organization banner and consent request form", async () => {
      renderWithAuth(<VerifierSearchPage />);

      expect(screen.getByText("Stakeholder Credential Verification")).toBeInTheDocument();
      await waitFor(() => {
        expect(screen.getByText(/AICTE Approved Verifier/i)).toBeInTheDocument();
      });
      expect(screen.getByLabelText(/Student 12-Digit APAAR ID/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Verification Purpose/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Request student consent" })).toBeInTheDocument();
    });

    it("populates demo APAAR ID on quick test button click and allows request initiation", async () => {
      renderWithAuth(<VerifierSearchPage />);

      const quickBtn = screen.getByText(/111122223333 \(Aarav Sharma\)/i);
      fireEvent.click(quickBtn);

      const apaarInput = screen.getByLabelText(/Student 12-Digit APAAR ID/i) as HTMLInputElement;
      expect(apaarInput.value).toBe("111122223333");

      const submitBtn = screen.getByRole("button", { name: "Request student consent" });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(screen.getByText(/Consent Request #/i)).toBeInTheDocument();
        expect(screen.getByText(/24-Hour Expiry Window/i)).toBeInTheDocument();
      });
    });
  });

  describe("VerifierHistoryPage", () => {
    it("renders consent history table, filter tabs, and action buttons", async () => {
      renderWithAuth(<VerifierHistoryPage />);

      expect(screen.getByText("Verification & Consent History")).toBeInTheDocument();
      expect(screen.getByText("All Requests")).toBeInTheDocument();
      expect(screen.getByText("Pending")).toBeInTheDocument();
      expect(screen.getByText("Approved")).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText("#101")).toBeInTheDocument();
        expect(screen.getByText("Pre-employment academic credential verification")).toBeInTheDocument();
      });
    });

    it("opens consented record modal when viewing approved request", async () => {
      renderWithAuth(<VerifierHistoryPage />);

      await waitFor(() => {
        expect(screen.getByText("#101")).toBeInTheDocument();
      });

      const viewBtn = screen.getByRole("button", { name: "View record" });
      fireEvent.click(viewBtn);

      await waitFor(() => {
        expect(screen.getByText("Consented Academic Verification")).toBeInTheDocument();
        expect(screen.getByText(/Zero PII Guaranteed/i)).toBeInTheDocument();
      });
    });
  });

  describe("VerifyPage APAAR Consent Guidance", () => {
    it("displays DPDP consent protocol required card when 12-digit APAAR is entered", async () => {
      renderWithAuth(<VerifyPage />, {
        user: null,
        token: null,
        isAuthenticated: false,
      });

      const input = screen.getByLabelText(/Verification Identifier/i);
      fireEvent.change(input, { target: { value: "111122223333" } });

      const verifyBtn = screen.getByRole("button", { name: "Verify credential" });
      fireEvent.click(verifyBtn);

      await waitFor(() => {
        expect(screen.getByText(/DPDP Consent Protocol Required/i)).toBeInTheDocument();
        expect(screen.getByText(/12-Digit Student APAAR ID Entered \(111122223333\)/i)).toBeInTheDocument();
        expect(screen.getByText(/Sign in as Verifier/i)).toBeInTheDocument();
        expect(screen.getByText(/Open Student Portal/i)).toBeInTheDocument();
      });
    });
  });

  describe("StudentPortalPage Consent Decisions", () => {
    it("allows student to approve pending consent request in dashboard", async () => {
      renderWithAuth(<StudentPortalPage />);

      // Step 1: Send OTP
      const sendOtpBtn = screen.getByRole("button", { name: "Send verification OTP" });
      fireEvent.click(sendOtpBtn);

      // Step 2: Fill OTP & Access records
      await waitFor(() => {
        expect(screen.getByLabelText(/6-Digit OTP/i)).toBeInTheDocument();
      });

      const otpInput = screen.getByLabelText(/6-Digit OTP/i);
      fireEvent.change(otpInput, { target: { value: "123456" } });

      const accessBtn = screen.getByRole("button", { name: "Access records" });
      fireEvent.click(accessBtn);

      // Step 3: Inspect pending requests and click approve
      await waitFor(() => {
        expect(screen.getByText("Aarav Sharma")).toBeInTheDocument();
        expect(screen.getByText("Pending Verification Consent Requests")).toBeInTheDocument();
      });

      const approveBtn = screen.getByRole("button", { name: "Approve consent" });
      fireEvent.click(approveBtn);

      await waitFor(() => {
        expect(screen.getByText(/Consent approved/i)).toBeInTheDocument();
      });
    });
  });
});
