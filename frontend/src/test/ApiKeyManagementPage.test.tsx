import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AuthContext, type AuthContextType } from "../auth/AuthContext";
import { ApiKeyManagementPage } from "../pages/ApiKeyManagementPage";
import * as apiKeysApi from "../api/apiKeys";

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

const mockKeysList: apiKeysApi.ApiKeyListResponse = {
  total: 2,
  items: [
    {
      id: 101,
      institution_id: 1,
      name: "Campus ERP Production",
      key_prefix: "apaar_live_a1b2...c3d4",
      scopes: ["students:write", "students:read"],
      created_at: "2026-10-20T10:00:00Z",
      last_used_at: "2026-10-25T14:30:00Z",
      revoked_at: null,
      is_active: true,
    },
    {
      id: 102,
      institution_id: 1,
      name: "Legacy SIS Ingestion",
      key_prefix: "apaar_live_e5f6...g7h8",
      scopes: ["students:read"],
      created_at: "2026-09-15T08:00:00Z",
      last_used_at: null,
      revoked_at: "2026-10-01T12:00:00Z",
      is_active: false,
    },
  ],
};

describe("T36: ApiKeyManagementPage UI Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders API keys list with badges, scopes, and quickstart documentation", async () => {
    vi.spyOn(apiKeysApi, "listApiKeys").mockResolvedValue(mockKeysList);

    renderWithAuth(<ApiKeyManagementPage />);

    expect(screen.getByText("Integration API Keys")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Campus ERP Production")).toBeInTheDocument();
      expect(screen.getByText("apaar_live_a1b2...c3d4")).toBeInTheDocument();
      expect(screen.getByText("Legacy SIS Ingestion")).toBeInTheDocument();
    });

    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Revoked")).toBeInTheDocument();
    expect(screen.getByText("ERP Integration Quickstart")).toBeInTheDocument();
  });

  it("opens creation modal and generates a new secret key with copy feedback", async () => {
    vi.spyOn(apiKeysApi, "listApiKeys").mockResolvedValue(mockKeysList);
    const createSpy = vi.spyOn(apiKeysApi, "createApiKey").mockResolvedValue({
      id: 103,
      institution_id: 1,
      name: "New Admissions Portal",
      key_prefix: "apaar_live_9988...7766",
      raw_key: "apaar_live_SUPER_SECRET_TOKEN_12345",
      scopes: ["students:write", "students:read"],
      created_at: "2026-10-28T09:00:00Z",
      last_used_at: null,
      revoked_at: null,
      is_active: true,
    });

    renderWithAuth(<ApiKeyManagementPage />);

    await waitFor(() => {
      expect(screen.getByText("Campus ERP Production")).toBeInTheDocument();
    });

    // Click "+ Generate New API Key"
    fireEvent.click(screen.getByRole("button", { name: /generate new api key/i }));

    // Form inputs in modal
    const nameInput = screen.getByPlaceholderText(/e\.g\. Campus ERP Production/i);
    fireEvent.change(nameInput, { target: { value: "New Admissions Portal" } });

    // Click submit
    fireEvent.click(screen.getByRole("button", { name: /generate secret key/i }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(1, {
        name: "New Admissions Portal",
        scopes: ["students:write", "students:read"],
      });
    });

    // Secret key display modal should now appear with raw key
    await waitFor(() => {
      expect(screen.getByText(/API Key Created Successfully!/i)).toBeInTheDocument();
      expect(screen.getByDisplayValue("apaar_live_SUPER_SECRET_TOKEN_12345")).toBeInTheDocument();
    });

    // Copy Key button
    expect(screen.getByRole("button", { name: /copy key/i })).toBeInTheDocument();
  });

  it("handles rotation flow with confirmation modal and displays new secret key", async () => {
    vi.spyOn(apiKeysApi, "listApiKeys").mockResolvedValue(mockKeysList);
    const rotateSpy = vi.spyOn(apiKeysApi, "rotateApiKey").mockResolvedValue({
      id: 101,
      institution_id: 1,
      name: "Campus ERP Production",
      key_prefix: "apaar_live_1122...3344",
      raw_key: "apaar_live_ROTATED_SECRET_KEY_9999",
      scopes: ["students:write", "students:read"],
      updated_at: "2026-10-28T09:15:00Z",
    });

    renderWithAuth(<ApiKeyManagementPage />);

    await waitFor(() => {
      expect(screen.getByText("Campus ERP Production")).toBeInTheDocument();
    });

    // Click Rotate on first key
    const rotateButtons = screen.getAllByRole("button", { name: /rotate/i });
    fireEvent.click(rotateButtons[0]);

    // Confirmation modal should show
    expect(screen.getByText(/Rotate API Key/i)).toBeInTheDocument();
    expect(screen.getByText(/immediately invalidate/i)).toBeInTheDocument();

    // Confirm rotation
    fireEvent.click(screen.getByRole("button", { name: /rotate key now/i }));

    await waitFor(() => {
      expect(rotateSpy).toHaveBeenCalledWith(1, 101);
      expect(screen.getByText(/API Key Rotated Successfully!/i)).toBeInTheDocument();
      expect(screen.getByDisplayValue("apaar_live_ROTATED_SECRET_KEY_9999")).toBeInTheDocument();
    });
  });

  it("handles revocation flow with confirmation modal", async () => {
    vi.spyOn(apiKeysApi, "listApiKeys").mockResolvedValue(mockKeysList);
    const revokeSpy = vi.spyOn(apiKeysApi, "revokeApiKey").mockResolvedValue({
      id: 101,
      institution_id: 1,
      name: "Campus ERP Production",
      key_prefix: "apaar_live_a1b2...c3d4",
      scopes: ["students:write"],
      created_at: "2026-10-20T10:00:00Z",
      last_used_at: null,
      revoked_at: "2026-10-28T09:20:00Z",
      is_active: false,
    });

    renderWithAuth(<ApiKeyManagementPage />);

    await waitFor(() => {
      expect(screen.getByText("Campus ERP Production")).toBeInTheDocument();
    });

    // Click Revoke on first key
    const revokeButtons = screen.getAllByRole("button", { name: /revoke/i });
    fireEvent.click(revokeButtons[0]);

    // Confirmation modal
    expect(screen.getByText(/permanently revoke this API key/i)).toBeInTheDocument();

    // Confirm revoke
    const confirmButtons = screen.getAllByRole("button", { name: /revoke key/i });
    fireEvent.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => {
      expect(revokeSpy).toHaveBeenCalledWith(1, 101);
    });
  });

  it("displays empty state when no keys exist", async () => {
    vi.spyOn(apiKeysApi, "listApiKeys").mockResolvedValue({ total: 0, items: [] });

    renderWithAuth(<ApiKeyManagementPage />);

    await waitFor(() => {
      expect(screen.getByText("No API Keys Generated Yet")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /generate first api key/i })).toBeInTheDocument();
    });
  });
});
