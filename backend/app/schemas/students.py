from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StudentBase(BaseModel):
    student_code: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    birth_date: date | None = None
    status: str = Field(default="ACTIVE", min_length=1, max_length=30)


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    birth_date: date | None = None
    status: str | None = Field(default=None, min_length=1, max_length=30)


class StudentResponse(StudentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StudentSummary(BaseModel):
    total: int
    active: int
    inactive: int