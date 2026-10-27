import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import type { Role } from "../types/auth";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";

interface ProtectedRouteProps {
  children?: React.ReactNode;
  allowedRoles?: Role[];
}

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <LoadingSpinner size="lg" label="Checking authorization..." />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    const isAictePath = location.pathname.startsWith("/aicte");
    const targetLogin = isAictePath ? "/login/aicte" : "/login/college";
    return <Navigate to={targetLogin} state={{ from: location }} replace />;
  }

  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" state={{ attemptedPath: location.pathname }} replace />;
  }

  return <>{children}</>;
}

export function GuestOnlyRoute({ children }: { children?: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <LoadingSpinner size="lg" label="Loading..." />
      </div>
    );
  }

  if (isAuthenticated && user) {
    if (user.role === "aicte_admin" || user.role === "aicte_officer") {
      return <Navigate to="/aicte/overview" replace />;
    }
    if (user.role === "verifier") {
      return <Navigate to="/verifier/search" replace />;
    }
    return <Navigate to="/college/dashboard" replace />;
  }

  return <>{children}</>;
}
