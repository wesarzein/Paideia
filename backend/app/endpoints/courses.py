from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import Course
from app.models.user import User
from app.schemas.courses import CourseCreate, CourseResponse, CourseUpdate

router = APIRouter()


@router.get("", response_model=list[CourseResponse])
def list_courses(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
) -> list[Course]:
    return db.scalars(select(Course).order_by(Course.name)).all()


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "coordinator")),
) -> Course:
    existing = db.scalar(select(Course).where(Course.code == payload.code.strip()))
    if existing is not None:
        raise HTTPException(status_code=409, detail="El código del curso ya existe")

    course = Course(name=payload.name.strip(), code=payload.code.strip())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return course


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(course_id: UUID, payload: CourseUpdate, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "coordinator"))) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: UUID, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "coordinator"))) -> None:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    db.delete(course)
    db.commit()
