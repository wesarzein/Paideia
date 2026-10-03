from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.follow_up import FollowUp
from app.models.academic import CourseAssignment
from app.models.student import Student
from app.models.user import User

router = APIRouter()


class FollowUpCreate(BaseModel):
    student_id: UUID
    category: str = Field(default="OBSERVATION", min_length=1, max_length=40)
    action: str = Field(min_length=3, max_length=500)
    status: str = "OPEN"


class FollowUpUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=40)
    action: str | None = Field(default=None, min_length=3, max_length=500)
    status: str | None = Field(default=None, min_length=1, max_length=30)


class FollowUpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    student_id: UUID
    recorded_by_id: UUID | None
    category: str
    action: str
    status: str


@router.get("", response_model=list[FollowUpResponse])
def list_follow_ups(
    grade_id: UUID | None = None,
    section_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
):
    statement = select(FollowUp).join(Student)
    if grade_id:
        statement = statement.where(Student.grade_id == grade_id)
    if section_id:
        statement = statement.where(Student.section_id == section_id)
    if user.role.code == "teacher":
        statement = statement.join(CourseAssignment, (CourseAssignment.grade_id == Student.grade_id) & (CourseAssignment.section_id == Student.section_id)).where(CourseAssignment.teacher_id == user.id)
    return db.scalars(statement.order_by(FollowUp.created_at.desc())).all()


@router.post("", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
def create_follow_up(
    payload: FollowUpCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
):
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    if user.role.code == "teacher" and db.scalar(select(CourseAssignment.id).where(CourseAssignment.grade_id == student.grade_id, CourseAssignment.section_id == student.section_id, CourseAssignment.teacher_id == user.id)) is None:
        raise HTTPException(status_code=403, detail="No tienes acceso al seguimiento de este estudiante")

    item = FollowUp(**payload.model_dump(), recorded_by_id=user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{follow_up_id}", response_model=FollowUpResponse)
def update_follow_up(
    follow_up_id: UUID,
    payload: FollowUpUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator")),
):
    item = db.get(FollowUp, follow_up_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    student = db.get(Student, item.student_id)
    if user.role.code == "teacher" and db.scalar(select(CourseAssignment.id).where(CourseAssignment.grade_id == student.grade_id, CourseAssignment.section_id == student.section_id, CourseAssignment.teacher_id == user.id)) is None:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este seguimiento")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{follow_up_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_follow_up(
    follow_up_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> None:
    item = db.get(FollowUp, follow_up_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    student = db.get(Student, item.student_id)
    if user.role.code == "teacher" and db.scalar(select(CourseAssignment.id).where(CourseAssignment.grade_id == student.grade_id, CourseAssignment.section_id == student.section_id, CourseAssignment.teacher_id == user.id)) is None:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este seguimiento")
    db.delete(item)
    db.commit()