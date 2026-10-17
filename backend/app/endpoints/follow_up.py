from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.follow_up import FollowUp
from app.models.student import Student
from app.models.user import User
from app.services.academic_access import student_scope

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
    created_at: datetime | None = None
    recorded_by_name: str | None = None


def response_for(item: FollowUp, author_name: str | None) -> FollowUpResponse:
    return FollowUpResponse.model_validate(item).model_copy(
        update={"recorded_by_name": author_name}
    )


@router.get("", response_model=list[FollowUpResponse])
def list_follow_ups(
    grade_id: UUID | None = None,
    section_id: UUID | None = None,
    student_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("coordinator")),
):
    statement = (
        select(FollowUp, User.full_name)
        .join(Student, FollowUp.student_id == Student.id)
        .outerjoin(User, FollowUp.recorded_by_id == User.id)
        .where(student_scope(user))
    )
    if grade_id:
        statement = statement.where(Student.grade_id == grade_id)
    if section_id:
        statement = statement.where(Student.section_id == section_id)
    if student_id:
        statement = statement.where(Student.id == student_id)
    return [
        response_for(item, author_name)
        for item, author_name in db.execute(
            statement.order_by(FollowUp.created_at.desc(), FollowUp.id.desc())
        )
    ]


@router.post("", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
def create_follow_up(
    payload: FollowUpCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("coordinator")),
):
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    item = FollowUp(**payload.model_dump(), recorded_by_id=user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return response_for(item, db.scalar(select(User.full_name).where(User.id == item.recorded_by_id)))


@router.patch("/{follow_up_id}", response_model=FollowUpResponse)
def update_follow_up(
    follow_up_id: UUID,
    payload: FollowUpUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("coordinator")),
):
    item = db.get(FollowUp, follow_up_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return response_for(item, db.scalar(select(User.full_name).where(User.id == item.recorded_by_id)))


@router.delete("/{follow_up_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_follow_up(
    follow_up_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("coordinator")),
) -> None:
    item = db.get(FollowUp, follow_up_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    db.delete(item)
    db.commit()
