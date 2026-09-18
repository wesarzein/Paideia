from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import engine
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/db", response_model=HealthResponse)
def database_health() -> HealthResponse:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return HealthResponse(status="ok")
