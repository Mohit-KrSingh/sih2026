import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextType } from "../auth/AuthContext";
import { CollegeLoginPage } from "../pages/CollegeLoginPage";
import { AicteLoginPage } from "../pages/AicteLoginPage";
import { VerifyPage } from "../pages/VerifyPage";
import { ActivatePage } from "../pages/ActivatePage";
import { StudentPortalPage } from "../pages/StudentPortalPage";

const baseMockAuth: AuthContextType = {
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  pendingMfa: null,
  login: vi.fn(),
  verifyMfa: vi.fn(),
  cancelMfa: vi.fn(),
  logout: vi.fn(),
  hasRole: vi.fn(),
  isCollege: false,
  isAicte: false,
  isAdmin: false,
  refreshUser: vi.fn(),
};

function renderWithAuth(ui: React.ReactNode, authState: Partial<AuthContextType> = {}) {
  const contextValue = { ...baseMockAuth, ...authState };
  return render(
    <AuthContext.Provider value={contextValue}>
      <MemoryRouter>{ui}</MemoryRouter>
    </AuthContext.Provider>
  );
}

describe("Public Pages", () => {
  describe("CollegeLoginPage", () => {
    it("renders credentials form with demo fill buttons", () => {
      renderWithAuth(<CollegeLoginPage />);

      expect(screen.getByText("College Portal Login")).toBeInTheDocument();
      expect(screen.getByLabelText(/Official Institutional Email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Sign in as college" })).toBeInTheDocument();

      // Demo college buttons exist
      expect(screen.getByText("Pune Inst. of Adv. Engg & Tech")).toBeInTheDocument();
      expect(screen.getByText("Mumbai Metropolitan Inst. of Tech")).toBeInTheDocument();
      expect(screen.getByText("Nagpur Govt Engineering College")).toBeInTheDocument();
    });

    it("fills demo credentials on clicking quick-fill button", () => {
      renderWithAuth(<CollegeLoginPage />);

      const demoBtn = screen.getByText("Pune Inst. of Adv. Engg & Tech");
      fireEvent.click(demoBtn);

      const emailInput = screen.getByLabelText(/Official Institutional Email/i) as HTMLInputElement;
      expect(emailInput.value).toBe("admin@piaet-pune.edu.in");
    });

    it("displays MFA verification form when pendingMfa is set", () => {
      const pendingMfa = {
        mfaToken: "intermediate-mfa-token",
        userSummary: {
          id: 1,
          email: "admin@piaet-pune.edu.in",
          role: "college_admin" as const,
          institution_id: 1,
          is_active: true,
        },
      };

      renderWithAuth(<CollegeLoginPage />, { pendingMfa });

      expect(screen.getByTestId("college-mfa-form")).toBeInTheDocument();
      expect(screen.getByLabelText(/Authenticator Code/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Verify and sign in" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    });
  });

  describe("AicteLoginPage", () => {
    it("renders AICTE login screen and demo buttons", () => {
      renderWithAuth(<AicteLoginPage />);

      expect(screen.getByText("AICTE Central Portal")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Sign in to AICTE portal" })).toBeInTheDocument();

      expect(screen.getByText("AICTE System Administrator")).toBeInTheDocument();
      expect(screen.getByText("AICTE Compliance Officer")).toBeInTheDocument();
    });

    it("fills AICTE demo account on quick-fill click", () => {
      renderWithAuth(<AicteLoginPage />);

      const adminBtn = screen.getByText("AICTE System Administrator");
      fireEvent.click(adminBtn);

      const emailInput = screen.getByLabelText(/Official AICTE Email/i) as HTMLInputElement;
      expect(emailInput.value).toBe("aicte_admin@aicte-india.org");
    });
  });

  describe("VerifyPage", () => {
    it("renders verification query input and explains Ed25519 signature", async () => {
      renderWithAuth(<VerifyPage />);

      expect(screen.getByText("Verify Student Academic Credential")).toBeInTheDocument();
      const input = screen.getByLabelText(/Verification Identifier/i);
      expect(input).toBeInTheDocument();

      // Quick demo verification button
      const sampleBtn = screen.getByText("VID-2026-PIAET-0042");
      fireEvent.click(sampleBtn);

      await waitFor(() => {
        expect(screen.getByText(/Cryptographically Valid Credential/i)).toBeInTheDocument();
        expect(screen.getByText(/Ed25519 Digital Signature Verified/i)).toBeInTheDocument();
        expect(screen.getByText(/Zero Personal Data Leak/i)).toBeInTheDocument();
      });
    });
  });

  describe("ActivatePage", () => {
    it("renders institution activation lookup form", async () => {
      renderWithAuth(<ActivatePage />);

      expect(screen.getByText("Activate Your Institution Account")).toBeInTheDocument();
      expect(screen.getByLabelText(/AICTE Institute Identifier/i)).toBeInTheDocument();

      const input = screen.getByLabelText(/AICTE Institute Identifier/i);
      fireEvent.change(input, { target: { value: "1-10000001" } });

      const verifyBtn = screen.getByRole("button", { name: "Verify institution" });
      fireEvent.click(verifyBtn);

      await waitFor(() => {
        expect(screen.getByText(/Institution Verified in AICTE Master Directory/i)).toBeInTheDocument();
        expect(screen.getByText("Pune Institute of Advanced Engineering & Technology")).toBeInTheDocument();
      });
    });
  });

  describe("StudentPortalPage", () => {
    it("renders student consent portal and allows demo login flow", async () => {
      renderWithAuth(<StudentPortalPage />);

      expect(screen.getByText("Student Consent & Record Portal")).toBeInTheDocument();
      expect(screen.getByLabelText(/APAAR Identification Number/i)).toBeInTheDocument();

      const sendOtpBtn = screen.getByRole("button", { name: "Send verification OTP" });
      fireEvent.click(sendOtpBtn);

      await waitFor(() => {
        expect(screen.getByLabelText(/6-Digit OTP/i)).toBeInTheDocument();
      });

      const otpInput = screen.getByLabelText(/6-Digit OTP/i);
      fireEvent.change(otpInput, { target: { value: "123456" } });

      const accessBtn = screen.getByRole("button", { name: "Access records" });
      fireEvent.click(accessBtn);

      await waitFor(() => {
        expect(screen.getByText("Aarav Sharma")).toBeInTheDocument();
        expect(screen.getByText(/Pune Institute of Advanced Engineering & Technology/i)).toBeInTheDocument();
      });
    });
  });
});
