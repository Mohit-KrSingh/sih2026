from fastapi import APIRouter

from app.analytics.router import router as analytics_router
from app.api_v1.dev import router as dev_router
from app.api_v1.health import router as health_router
from app.api_v1.privacy import router as privacy_router
from app.audit.router import router as audit_router
from app.auth.api_keys_router import router as api_keys_router
from app.auth.router import router as auth_router
from app.institutions.router import router as institutions_router
from app.reports.router import institution_reports_router
from app.reports.router import router as reports_router
from app.review.router import college_queries_router
from app.review.router import router as review_router
from app.students.change_request_router import aicte_router as aicte_change_requests_router
from app.students.change_request_router import college_router as college_change_requests_router
from app.students.integration_router import router as integration_router
from app.students.router import router as students_router
from app.submissions.router import router as submissions_router
from app.validation.router import router as rules_router
from app.verification.router import router as verification_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(privacy_router)
api_v1_router.include_router(dev_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(api_keys_router)
api_v1_router.include_router(institutions_router)
api_v1_router.include_router(students_router)
api_v1_router.include_router(integration_router)
api_v1_router.include_router(submissions_router)
api_v1_router.include_router(verification_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(rules_router)
api_v1_router.include_router(review_router)
api_v1_router.include_router(college_queries_router)
api_v1_router.include_router(college_change_requests_router)
api_v1_router.include_router(aicte_change_requests_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(institution_reports_router)
