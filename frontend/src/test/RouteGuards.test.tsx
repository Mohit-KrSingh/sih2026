import { render, screen } from "@testing-library/react";
import React from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextType } from "../auth/AuthContext";
import { GuestOnlyRoute, ProtectedRoute } from "../auth/RouteGuards";
import type { User } from "../types/auth";

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

function renderWithAuth(ui: React.ReactNode, authState: Partial<AuthContextType>, initialPath = "/") {
  const contextValue = { ...baseMockAuth, ...authState };
  return render(
    <AuthContext.Provider value={contextValue}>
      <MemoryRouter initialEntries={[initialPath]}>
        {ui}
      </MemoryRouter>
    </AuthContext.Provider>
  );
}

describe("RouteGuards", () => {
  it("redirects unauthenticated user to /login/college for college routes", () => {
    renderWithAuth(
      <Routes>
        <Route
          path="/college/dashboard"
          element={
            <ProtectedRoute allowedRoles={["college_admin"]}>
              <div>College Dashboard Content</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login/college" element={<div>College Login Page</div>} />
      </Routes>,
      { isAuthenticated: false, user: null, isLoading: false },
      "/college/dashboard"
    );

    expect(screen.getByText("College Login Page")).toBeInTheDocument();
    expect(screen.queryByText("College Dashboard Content")).not.toBeInTheDocument();
  });

  it("redirects unauthenticated user to /login/aicte for AICTE routes", () => {
    renderWithAuth(
      <Routes>
        <Route
          path="/aicte/overview"
          element={
            <ProtectedRoute allowedRoles={["aicte_admin"]}>
              <div>AICTE Overview Content</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login/aicte" element={<div>AICTE Login Page</div>} />
      </Routes>,
      { isAuthenticated: false, user: null, isLoading: false },
      "/aicte/overview"
    );

    expect(screen.getByText("AICTE Login Page")).toBeInTheDocument();
    expect(screen.queryByText("AICTE Overview Content")).not.toBeInTheDocument();
  });

  it("permits authorized user matching allowed role", () => {
    const collegeUser: User = {
      id: 1,
      email: "principal@sdpea.ac.in",
      role: "college_admin",
      institution_id: 1,
      is_active: true,
    };

    renderWithAuth(
      <Routes>
        <Route
          path="/college/dashboard"
          element={
            <ProtectedRoute allowedRoles={["college_admin"]}>
              <div>College Dashboard Content</div>
            </ProtectedRoute>
          }
        />
      </Routes>,
      { isAuthenticated: true, user: collegeUser, isLoading: false },
      "/college/dashboard"
    );

    expect(screen.getByText("College Dashboard Content")).toBeInTheDocument();
  });

  it("redirects user with mismatched role to /unauthorized", () => {
    const collegeUser: User = {
      id: 1,
      email: "staff@piaet.ac.in",
      role: "college_staff",
      institution_id: 1,
      is_active: true,
    };

    renderWithAuth(
      <Routes>
        <Route
          path="/aicte/overview"
          element={
            <ProtectedRoute allowedRoles={["aicte_admin", "aicte_officer"]}>
              <div>AICTE Secret Content</div>
            </ProtectedRoute>
          }
        />
        <Route path="/unauthorized" element={<div>403 Unauthorized Screen</div>} />
      </Routes>,
      { isAuthenticated: true, user: collegeUser, isLoading: false },
      "/aicte/overview"
    );

    expect(screen.getByText("403 Unauthorized Screen")).toBeInTheDocument();
    expect(screen.queryByText("AICTE Secret Content")).not.toBeInTheDocument();
  });

  it("GuestOnlyRoute redirects logged-in college user to dashboard", () => {
    const collegeUser: User = {
      id: 1,
      email: "admin@piaet.edu.in",
      role: "college_admin",
      institution_id: 1,
      is_active: true,
    };

    renderWithAuth(
      <Routes>
        <Route
          path="/login/college"
          element={
            <GuestOnlyRoute>
              <div>Login Form</div>
            </GuestOnlyRoute>
          }
        />
        <Route path="/college/dashboard" element={<div>College Dashboard Redirect</div>} />
      </Routes>,
      { isAuthenticated: true, user: collegeUser, isLoading: false },
      "/login/college"
    );

    expect(screen.getByText("College Dashboard Redirect")).toBeInTheDocument();
    expect(screen.queryByText("Login Form")).not.toBeInTheDocument();
  });
});
