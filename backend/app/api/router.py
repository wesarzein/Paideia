from fastapi import APIRouter

from app.endpoints.attendance import router as attendance_router
from app.endpoints.academic import router as academic_router
from app.endpoints.auth import router as auth_router
from app.endpoints.courses import router as courses_router
from app.endpoints.dashboard import router as dashboard_router
from app.endpoints.enrollments import router as enrollments_router
from app.endpoints.grades import router as grades_router
from app.endpoints.health import router as health_router
from app.endpoints.follow_up import router as follow_up_router
from app.endpoints.imports import router as imports_router
from app.endpoints.kpis import router as kpis_router
from app.endpoints.reports import router as reports_router
from app.endpoints.students import router as students_router
from app.endpoints.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(students_router, prefix="/students", tags=["students"])
api_router.include_router(courses_router, prefix="/courses", tags=["courses"])
api_router.include_router(enrollments_router, prefix="/enrollments", tags=["enrollments"])
api_router.include_router(grades_router, prefix="/grades", tags=["grades"])
api_router.include_router(attendance_router, prefix="/attendance", tags=["attendance"])
api_router.include_router(academic_router, prefix="/academic", tags=["academic"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(imports_router, prefix="/imports", tags=["imports"])
api_router.include_router(kpis_router, prefix="/kpis", tags=["kpis"])
api_router.include_router(follow_up_router, prefix="/follow-ups", tags=["follow-ups"])
