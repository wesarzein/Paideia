from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AcademicPeriod, Course, Enrollment
from app.models.student import Student
from app.models.user import User
from app.schemas.courses import EnrollmentCreate, EnrollmentResponse, EnrollmentUpdate
from app.services.academic_access import ensure_student_course_access, record_scope

router = APIRouter()


@router.get("", response_model=list[EnrollmentResponse])
def list_enrollments(
    student_id: UUID | None = None,
    course_id: UUID | None = None,
    period_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
) -> list[Enrollment]:
    query = select(Enrollment).where(record_scope(Enrollment, _user))
    for field, value in (
        (Enrollment.student_id, student_id),
        (Enrollment.course_id, course_id),
        (Enrollment.period_id, period_id),
    ):
        if value is not None:
            query = query.where(field == value)
    return db.scalars(query.order_by(Enrollment.created_at.desc(), Enrollment.id)).all()


@router.post("", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
def create_enrollment(
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin")),
) -> Enrollment:
    if not db.get(Student, payload.student_id):
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    if not db.get(Course, payload.course_id):
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    if not db.get(AcademicPeriod, payload.period_id):
        raise HTTPException(status_code=404, detail="Periodo no encontrado")
    if _user.role.code == "teacher":
        ensure_student_course_access(db, _user, db.get(Student, payload.student_id),
                                     payload.course_id, payload.period_id)

    if db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"enrollment:{payload.student_id}:{payload.course_id}:{payload.period_id}"},
        )

    duplicate = db.scalar(select(Enrollment).where(Enrollment.student_id == payload.student_id, Enrollment.course_id == payload.course_id, Enrollment.period_id == payload.period_id))
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="La matrícula ya existe")
    enrollment = Enrollment(
        student_id=payload.student_id,
        course_id=payload.course_id,
        period_id=payload.period_id,
        status=payload.status.strip().upper(),
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.patch("/{enrollment_id}", response_model=EnrollmentResponse)
def update_enrollment(enrollment_id: UUID, payload: EnrollmentUpdate, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin"))) -> Enrollment:
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada")
    enrollment.status = payload.status.strip().upper()
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_enrollment(enrollment_id: UUID, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin"))) -> None:
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada")
    db.delete(enrollment)
    db.commit()


@router.get("/{enrollment_id}", response_model=EnrollmentResponse)
def get_enrollment(
    enrollment_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
) -> Enrollment:
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Matricula no encontrada")
    if db.scalar(select(Enrollment.id).where(
        Enrollment.id == enrollment.id, record_scope(Enrollment, _user)
    )) is None:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta matrícula")
    return enrollment
