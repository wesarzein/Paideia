from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.student import Student
from app.schemas.students import StudentCreate, StudentResponse, StudentSummary, StudentUpdate

router = APIRouter()


@router.get("", response_model=list[StudentResponse])
def list_students(
    search: str | None = Query(default=None, max_length=100),
    student_status: str | None = Query(default=None, alias="status", max_length=30),
    db: Session = Depends(get_db),  # noqa: B008
) -> list[Student]:
    statement = select(Student).order_by(Student.last_name, Student.first_name)
    if search:
        search_term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Student.student_code.ilike(search_term),
                Student.first_name.ilike(search_term),
                Student.last_name.ilike(search_term),
            )
        )
    if student_status:
        statement = statement.where(Student.status == student_status)
    return list(db.scalars(statement).all())


@router.get("/summary", response_model=StudentSummary)
def student_summary(db: Session = Depends(get_db)) -> StudentSummary:  # noqa: B008
    total = db.scalar(select(func.count()).select_from(Student)) or 0
    active = db.scalar(select(func.count()).where(Student.status == "ACTIVE")) or 0
    return StudentSummary(total=total, active=active, inactive=total - active)


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)) -> Student:  # noqa: B008
    student = Student(**payload.model_dump())
    db.add(student)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="El código del estudiante ya existe") from error
    db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: UUID, db: Session = Depends(get_db)) -> Student:  # noqa: B008
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return student


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: UUID, payload: StudentUpdate, db: Session = Depends(get_db)  # noqa: B008
) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: UUID, db: Session = Depends(get_db)) -> None:  # noqa: B008
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    db.delete(student)
    db.commit()