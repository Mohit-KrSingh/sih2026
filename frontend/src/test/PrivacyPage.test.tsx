import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { PrivacyPage } from "../pages/PrivacyPage";
import { Footer } from "../components/layout/Footer";

describe("PrivacyPage & DPDP Compliance", () => {
  it("renders DPDP Privacy Page header, badges, and statutory fiduciary notice", () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>
    );

    expect(
      screen.getByText("Digital Personal Data Protection (DPDP) Act, 2023 Compliant")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Privacy Policy & Data Minimisation Charter")
    ).toBeInTheDocument();
    expect(
      screen.getByText("All India Council for Technical Education (AICTE)")
    ).toBeInTheDocument();
  });

  it("renders DPDP core metric cards", () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>
    );

    expect(screen.getByText("16 Fields Only")).toBeInTheDocument();
    expect(screen.getByText("Strict Data Minimisation")).toBeInTheDocument();
    expect(screen.getByText("100% Consented")).toBeInTheDocument();
    expect(screen.getByText("24-Hour TTL")).toBeInTheDocument();
    expect(screen.getByText("AES-128 / Fernet")).toBeInTheDocument();
  });

  it("renders all four core privacy pillars", () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>
    );

    expect(screen.getByText("1. Purpose Limitation")).toBeInTheDocument();
    expect(screen.getByText("2. Student Consent Framework")).toBeInTheDocument();
    expect(screen.getByText("3. Cryptographic Safeguards")).toBeInTheDocument();
    expect(screen.getByText("4. Student Statutory Rights")).toBeInTheDocument();
  });

  it("interactively toggles between collected fields and prohibited personal data categories", () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>
    );

    // Initial tab: Collected Fields
    expect(screen.getByText("apaar_id")).toBeInTheDocument();
    expect(screen.getByText("enrolment_no")).toBeInTheDocument();
    expect(screen.getByText("dob")).toBeInTheDocument();

    // Switch to Prohibited Fields tab
    const prohibitedTabBtn = screen.getByRole("button", { name: /Prohibited Fields/i });
    fireEvent.click(prohibitedTabBtn);

    // Verify prohibited categories appear
    expect(screen.getByText("Aadhaar / National Identity Numbers")).toBeInTheDocument();
    expect(screen.getByText("Residential Address & Geolocation Data")).toBeInTheDocument();
    expect(screen.getByText("Photographs & Biometric Signatures")).toBeInTheDocument();
    expect(screen.getByText("Family Income & Financial Statements")).toBeInTheDocument();
    expect(screen.getByText("Examination Marks & Academic Transcripts")).toBeInTheDocument();

    // Switch back to Collected Fields tab
    const collectedTabBtn = screen.getByRole("button", { name: /Collected Fields/i });
    fireEvent.click(collectedTabBtn);

    expect(screen.getByText("apaar_id")).toBeInTheDocument();
  });

  it("renders the Statutory Grievance Redressal and DPO contact information", () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>
    );

    expect(
      screen.getByText("Statutory Grievance Redressal & Data Protection Officer (DPO)")
    ).toBeInTheDocument();
    expect(screen.getByText("dpo@aicte-india.org")).toBeInTheDocument();
    expect(
      screen.getByText(/All India Council for Technical Education, Nelson Mandela Marg/i)
    ).toBeInTheDocument();
  });

  it("renders the Footer with a link to /privacy", () => {
    render(
      <MemoryRouter>
        <Footer />
      </MemoryRouter>
    );

    const privacyLinks = screen.getAllByRole("link", { name: /Privacy/i });
    expect(privacyLinks.length).toBeGreaterThan(0);
    expect(privacyLinks[0]).toHaveAttribute("href", "/privacy");
  });
});
