from fastapi import APIRouter

from app.endpoints.health import router as health_router
from app.endpoints.students import router as students_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(students_router, prefix="/students", tags=["students"])
