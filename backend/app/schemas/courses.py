from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=40)


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=40)


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    created_at: datetime | None = None


class EnrollmentCreate(BaseModel):
    student_id: UUID
    course_id: UUID
    period_id: UUID
    status: str = Field(default="ACTIVE", min_length=1, max_length=30)


class EnrollmentUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    course_id: UUID
    period_id: UUID
    status: str
    created_at: datetime | None = None
