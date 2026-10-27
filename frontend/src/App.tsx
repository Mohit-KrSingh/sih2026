import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { GuestOnlyRoute, ProtectedRoute } from "./auth/RouteGuards";
import { PublicLayout } from "./components/layout/PublicLayout";
import { AppLayout } from "./components/layout/AppLayout";
import { HomePage } from "./pages/HomePage";
import { CollegeLoginPage } from "./pages/CollegeLoginPage";
import { AicteLoginPage } from "./pages/AicteLoginPage";
import { VerifyPage } from "./pages/VerifyPage";
import { ActivatePage } from "./pages/ActivatePage";
import { StudentPortalPage } from "./pages/StudentPortalPage";
import { UnauthorizedPage } from "./pages/UnauthorizedPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { CollegeDashboardPlaceholder } from "./pages/CollegeDashboardPlaceholder";
import { AicteOverviewPlaceholder } from "./pages/AicteOverviewPlaceholder";
import { AicteApprovalsPage } from "./pages/AicteApprovalsPage";
import { AicteIntakePage } from "./pages/AicteIntakePage";
import { GenericPlaceholder } from "./pages/GenericPlaceholder";
import type { Role } from "./types/auth";

const COLLEGE_ROLES: Role[] = ["college_admin", "college_staff", "college_viewer"];
const AICTE_ROLES: Role[] = ["aicte_admin", "aicte_officer"];
const VERIFIER_ROLES: Role[] = ["verifier", "aicte_admin"];

export function AppRoutes() {
  return (
    <Routes>
      {/* Public Pages */}
      <Route
        path="/"
        element={
          <PublicLayout>
            <HomePage />
          </PublicLayout>
        }
      />
      <Route
        path="/activate"
        element={
          <PublicLayout>
            <ActivatePage />
          </PublicLayout>
        }
      />
      <Route
        path="/verify"
        element={
          <PublicLayout>
            <VerifyPage />
          </PublicLayout>
        }
      />
      <Route
        path="/student"
        element={
          <PublicLayout>
            <StudentPortalPage />
          </PublicLayout>
        }
      />
      <Route
        path="/unauthorized"
        element={
          <PublicLayout>
            <UnauthorizedPage />
          </PublicLayout>
        }
      />

      {/* Guest-only Login Routes */}
      <Route
        path="/login/college"
        element={
          <GuestOnlyRoute>
            <PublicLayout>
              <CollegeLoginPage />
            </PublicLayout>
          </GuestOnlyRoute>
        }
      />
      <Route
        path="/login/aicte"
        element={
          <GuestOnlyRoute>
            <PublicLayout>
              <AicteLoginPage />
            </PublicLayout>
          </GuestOnlyRoute>
        }
      />

      {/* Protected College Routes */}
      <Route
        path="/college/dashboard"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <CollegeDashboardPlaceholder />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/seats"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Seat Declarations" section="College Portal" taskRef="T19" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/students"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Student Records Directory" section="College Portal" taskRef="T20" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/students/new"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Add Student Entry" section="College Portal" taskRef="T20" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/upload"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Bulk CSV / Excel Upload" section="College Portal" taskRef="T21" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/validation"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Validation Flags & Justifications" section="College Portal" taskRef="T24" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/submit"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Final Data Submission" section="College Portal" taskRef="T26" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/queries"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="AICTE Officer Queries" section="College Portal" taskRef="T25" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/change-requests"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Contact & Head Change Requests" section="College Portal" taskRef="T09" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/staff"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Staff Management" section="College Portal" taskRef="T09" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/api-keys"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="ERP Integration API Keys" section="College Portal" taskRef="T36" />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* Protected AICTE Routes */}
      <Route
        path="/aicte/overview"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <AicteOverviewPlaceholder />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/approvals"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <AicteApprovalsPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/intake"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <AicteIntakePage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/compliance"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Over-Intake Compliance Monitor" section="AICTE Central" taskRef="T28" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/duplicates"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Cross-College Duplicate Enrolments" section="AICTE Central" taskRef="T27" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/anomalies"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="ML Anomaly Detection" section="AICTE Central" taskRef="T29" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/review"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Submission Review Queue" section="AICTE Central" taskRef="T25" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/explore"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Data Explorer & Filters" section="AICTE Central" taskRef="T30" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/reports"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="National Reports & Exports" section="AICTE Central" taskRef="T31" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/audit"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Hash-Chained Audit Trail" section="AICTE Central" taskRef="T06" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/verifiers"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Third-Party Verifier Management" section="AICTE Central" taskRef="T33" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/rules"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Validation Rule Configuration" section="AICTE Central" taskRef="T12" />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* Protected Verifier Routes */}
      <Route
        path="/verifier/search"
        element={
          <ProtectedRoute allowedRoles={VERIFIER_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Stakeholder Credential Verification" section="Verifier Portal" taskRef="T32" />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/verifier/history"
        element={
          <ProtectedRoute allowedRoles={VERIFIER_ROLES}>
            <AppLayout>
              <GenericPlaceholder title="Verification & Consent History" section="Verifier Portal" taskRef="T32" />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* 404 Catch-All */}
      <Route
        path="*"
        element={
          <PublicLayout>
            <NotFoundPage />
          </PublicLayout>
        }
      />
    </Routes>
  );
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
