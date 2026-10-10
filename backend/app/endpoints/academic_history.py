from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic_history import AcademicChangeHistory
from app.models.student import Student
from app.models.user import User
from app.services.academic_access import ensure_student_read_access, student_scope

router = APIRouter()


@router.get("/history")
def history(
    student_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles("admin", "teacher", "coordinator", "director"))],
    record_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(404, "Estudiante no encontrado")
    ensure_student_read_access(db, user, student)
    model = AcademicChangeHistory
    scope = (
        select(Student.id)
        .where(
            Student.id == model.student_id,
            or_(
                (model.course_id.is_(None)) & student_scope(user),
                student_scope(user, model.course_id),
            ),
        )
        .correlate_except(Student)
        .exists()
    )
    query = select(model).where(model.student_id == student_id, scope)
    if record_id:
        query = query.where(model.record_id == record_id)
    rows = db.scalars(
        query.order_by(model.created_at.desc(), model.id.desc()).offset(offset).limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "entity": r.entity,
            "record_id": str(r.record_id),
            "operation": r.operation,
            "actor_id": str(r.actor_id) if r.actor_id else None,
            "actor_role": r.actor_role,
            "source": r.source,
            "authorization": r.authorization,
            "created_at": r.created_at,
            "before": r.before,
            "after": r.after,
        }
        for r in rows
    ]
