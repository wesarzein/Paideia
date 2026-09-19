from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AcademicPeriod, Course, GradeRecord
from app.models.student import Student
from app.models.user import User
from app.schemas.grades import GradeCreate, GradeResponse, GradeSummary, GradeUpdate

router = APIRouter()


@router.get("", response_model=list[GradeResponse])
def list_grades(student_id: UUID | None = None, course_id: UUID | None = None, period_id: UUID | None = None, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "teacher"))) -> list[GradeRecord]:
    statement = select(GradeRecord)
    if student_id: statement = statement.where(GradeRecord.student_id == student_id)
    if course_id: statement = statement.where(GradeRecord.course_id == course_id)
    if period_id: statement = statement.where(GradeRecord.period_id == period_id)
    return db.scalars(statement.order_by(GradeRecord.created_at.desc())).all()


@router.post("", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
def create_grade(
    payload: GradeCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher")),
) -> GradeRecord:
    if not db.get(Student, payload.student_id):
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    if not db.get(Course, payload.course_id):
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    if not db.get(AcademicPeriod, payload.period_id):
        raise HTTPException(status_code=404, detail="Periodo no encontrado")

    from app.models.academic import Enrollment
    if db.scalar(select(Enrollment).where(Enrollment.student_id == payload.student_id, Enrollment.course_id == payload.course_id, Enrollment.period_id == payload.period_id, Enrollment.status == "ACTIVE")) is None:
        raise HTTPException(status_code=409, detail="El estudiante no está matriculado en el curso y periodo")

    record = GradeRecord(
        student_id=payload.student_id,
        course_id=payload.course_id,
        period_id=payload.period_id,
        score=float(payload.score),
        qualitative_note=payload.qualitative_note,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/{grade_id}", response_model=GradeResponse)
def update_grade(grade_id: UUID, payload: GradeUpdate, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "teacher"))) -> GradeRecord:
    record = db.get(GradeRecord, grade_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Calificación no encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items(): setattr(record, field, value)
    db.commit(); db.refresh(record)
    return record


@router.delete("/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade(grade_id: UUID, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "teacher"))) -> None:
    record = db.get(GradeRecord, grade_id)
    if record is None: raise HTTPException(status_code=404, detail="Calificación no encontrada")
    db.delete(record); db.commit()


@router.get("/summary/{student_id}", response_model=GradeSummary)
def summary_by_student(student_id: UUID, db: Session = Depends(get_db)) -> GradeSummary:
    results = db.execute(
        select(GradeRecord.score).where(GradeRecord.student_id == student_id)
    ).scalars().all()
    if not results:
        return GradeSummary(student_id=student_id, average=0.0, count=0)
    average = sum(results) / len(results)
    return GradeSummary(student_id=student_id, average=average, count=len(results))
