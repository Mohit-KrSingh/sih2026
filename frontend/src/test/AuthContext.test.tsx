import { act, renderHook } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "../auth/AuthContext";
import * as authApi from "../api/auth";
import * as clientApi from "../api/client";
import type { TokenResponse, User } from "../types/auth";

const mockCollegeUser: User = {
  id: 1,
  email: "admin@piaet-pune.edu.in",
  role: "college_admin",
  institution_id: 1,
  is_active: true,
};

const mockAicteUser: User = {
  id: 2,
  email: "aicte_admin@aicte-india.org",
  role: "aicte_admin",
  institution_id: null,
  is_active: true,
};

describe("AuthContext", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  );

  it("initializes as unauthenticated when no stored token", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {});

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it("restores user session when valid token in localStorage", async () => {
    localStorage.setItem("apaar_access_token", "valid-jwt-token");
    vi.spyOn(authApi, "getMeApi").mockResolvedValue(mockCollegeUser);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {});

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.email).toBe("admin@piaet-pune.edu.in");
    expect(result.current.isCollege).toBe(true);
    expect(result.current.isAicte).toBe(false);
    expect(result.current.isAdmin).toBe(true);
  });

  it("handles successful direct login without MFA", async () => {
    const loginResponse: TokenResponse = {
      access_token: "access-123",
      refresh_token: "refresh-123",
      token_type: "bearer",
      expires_in: 1800,
      user: mockCollegeUser,
      mfa_required: false,
    };

    vi.spyOn(authApi, "loginApi").mockResolvedValue(loginResponse);

    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {});

    let loginResult: { mfaRequired: boolean } | undefined;
    await act(async () => {
      loginResult = await result.current.login({
        email: "admin@piaet-pune.edu.in",
        password: "Password@123",
      });
    });

    expect(loginResult?.mfaRequired).toBe(false);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.email).toBe("admin@piaet-pune.edu.in");
    expect(result.current.pendingMfa).toBeNull();
  });

  it("handles MFA required login flow", async () => {
    const mfaRequiredResponse: TokenResponse = {
      access_token: "",
      refresh_token: "",
      token_type: "bearer",
      expires_in: 300,
      user: mockAicteUser,
      mfa_required: true,
      mfa_token: "mfa-intermediate-jwt",
    };

    vi.spyOn(authApi, "loginApi").mockResolvedValue(mfaRequiredResponse);

    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {});

    let loginResult: { mfaRequired: boolean } | undefined;
    await act(async () => {
      loginResult = await result.current.login({
        email: "aicte_admin@aicte-india.org",
        password: "AdminPassword@123",
      });
    });

    expect(loginResult?.mfaRequired).toBe(true);
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.pendingMfa).not.toBeNull();
    expect(result.current.pendingMfa?.mfaToken).toBe("mfa-intermediate-jwt");

    // Complete MFA step
    const mfaVerifyResponse: TokenResponse = {
      access_token: "verified-access-token",
      refresh_token: "verified-refresh-token",
      token_type: "bearer",
      expires_in: 1800,
      user: mockAicteUser,
    };
    vi.spyOn(authApi, "verifyMfaApi").mockResolvedValue(mfaVerifyResponse);

    await act(async () => {
      await result.current.verifyMfa("123456");
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.role).toBe("aicte_admin");
    expect(result.current.isAicte).toBe(true);
    expect(result.current.pendingMfa).toBeNull();
  });

  it("clears user and tokens on logout", async () => {
    localStorage.setItem("apaar_access_token", "existing-token");
    vi.spyOn(authApi, "getMeApi").mockResolvedValue(mockCollegeUser);

    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {});

    expect(result.current.isAuthenticated).toBe(true);

    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(clientApi.getStoredToken()).toBeNull();
  });
});
