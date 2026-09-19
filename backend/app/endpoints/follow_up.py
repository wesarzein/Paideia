from uuid import UUID
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.follow_up import FollowUp
from app.models.user import User

router = APIRouter()

class FollowUpCreate(BaseModel):
    student_id: UUID
    action: str = Field(min_length=3, max_length=500)
    status: str = "OPEN"

@router.get("")
def list_follow_ups(db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "teacher", "coordinator", "director"))):
    return db.scalars(select(FollowUp).order_by(FollowUp.created_at.desc())).all()

@router.post("", status_code=status.HTTP_201_CREATED)
def create_follow_up(payload: FollowUpCreate, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "teacher", "coordinator", "director"))):
    item = FollowUp(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item