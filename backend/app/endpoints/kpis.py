from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.user import User
from app.services.business_metrics import indicators

router = APIRouter()


@router.get("")
def calculate_kpis(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles("admin", "teacher", "coordinator", "director"))],
    grade_id: UUID | None = None,
    section_id: UUID | None = None,
    course_id: UUID | None = None,
    period_id: UUID | None = None,
    student_id: UUID | None = None,
    level: str | None = Query(default=None, max_length=80),
    bimester: int | None = Query(default=None, ge=1, le=100),
):
    return indicators(
        db,
        user,
        {
            "grade_id": grade_id,
            "section_id": section_id,
            "course_id": course_id,
            "period_id": period_id,
            "student_id": student_id,
            "level": level,
            "bimester": bimester,
        },
    )
