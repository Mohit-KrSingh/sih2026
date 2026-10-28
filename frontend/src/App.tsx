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
import { CollegeDashboardPage } from "./pages/CollegeDashboardPage";
import { AicteOverviewPage } from "./pages/AicteOverviewPage";
import { AicteApprovalsPage } from "./pages/AicteApprovalsPage";
import { AicteIntakePage } from "./pages/AicteIntakePage";
import { AicteCompliancePage } from "./pages/AicteCompliancePage";
import { AicteDuplicatesPage } from "./pages/AicteDuplicatesPage";
import { AicteAnomaliesPage } from "./pages/AicteAnomaliesPage";
import { AicteDrilldownPage } from "./pages/AicteDrilldownPage";
import { AicteRulesPage } from "./pages/AicteRulesPage";
import { AicteAuditPage } from "./pages/AicteAuditPage";
import { SeatDeclarationsPage } from "./pages/SeatDeclarationsPage";
import { StudentsListPage } from "./pages/StudentsListPage";
import { StudentFormPage } from "./pages/StudentFormPage";
import { BulkUploadPage } from "./pages/BulkUploadPage";
import { ValidationPage } from "./pages/ValidationPage";
import { SubmitPage } from "./pages/SubmitPage";
import { AicteReviewPage } from "./pages/AicteReviewPage";
import { AicteChangeRequestsPage } from "./pages/AicteChangeRequestsPage";
import { CollegeQueriesPage } from "./pages/CollegeQueriesPage";
import { CollegeChangeRequestsPage } from "./pages/CollegeChangeRequestsPage";
import { AicteReportsPage } from "./pages/AicteReportsPage";
import { VerifierSearchPage } from "./pages/VerifierSearchPage";
import { VerifierHistoryPage } from "./pages/VerifierHistoryPage";
import { ApiKeyManagementPage } from "./pages/ApiKeyManagementPage";
import { PrivacyPage } from "./pages/PrivacyPage";
import { StudentDetailPage } from "./pages/StudentDetailPage";
import { FlagDetailPage } from "./pages/FlagDetailPage";
import { ReviewItemDetailPage } from "./pages/ReviewItemDetailPage";
import { SubmissionDetailPage } from "./pages/SubmissionDetailPage";
import { StaffManagementPage } from "./pages/StaffManagementPage";
import { AicteVerifiersPage } from "./pages/AicteVerifiersPage";
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
        path="/privacy"
        element={
          <PublicLayout>
            <PrivacyPage />
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
              <CollegeDashboardPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/seats"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <SeatDeclarationsPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/students"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <StudentsListPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/students/new"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <StudentFormPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/students/:id"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <StudentDetailPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/students/:id/edit"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <StudentFormPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/upload"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <BulkUploadPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/validation"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <ValidationPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/validation/:flagId"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <FlagDetailPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/submit"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <SubmitPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/submissions/:id"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <SubmissionDetailPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/queries"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <CollegeQueriesPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/change-requests"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <CollegeChangeRequestsPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/staff"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <StaffManagementPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/college/api-keys"
        element={
          <ProtectedRoute allowedRoles={COLLEGE_ROLES}>
            <AppLayout>
              <ApiKeyManagementPage />
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
              <AicteOverviewPage />
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
              <AicteCompliancePage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/duplicates"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <AicteDuplicatesPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/anomalies"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <AicteAnomaliesPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/review"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <AicteReviewPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/review/:id"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <ReviewItemDetailPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/submissions/:id"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <SubmissionDetailPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/change-requests"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <AicteChangeRequestsPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/explore"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <AicteDrilldownPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/reports"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <AicteReportsPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/audit"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <AicteAuditPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/verifiers"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <AicteVerifiersPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/aicte/rules"
        element={
          <ProtectedRoute allowedRoles={AICTE_ROLES}>
            <AppLayout>
              <AicteRulesPage />
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
              <VerifierSearchPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/verifier/history"
        element={
          <ProtectedRoute allowedRoles={VERIFIER_ROLES}>
            <AppLayout>
              <VerifierHistoryPage />
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
