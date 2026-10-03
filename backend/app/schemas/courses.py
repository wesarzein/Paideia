from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=40)
    is_active: bool = True


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=40)
    is_active: bool | None = None


class AssessmentComponentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    weight: float = Field(default=1.0, ge=0, le=100)
    is_optional: bool = False


class AssessmentComponentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    weight: float | None = Field(default=None, ge=0, le=100)
    is_optional: bool | None = None
    is_active: bool | None = None


class AssessmentComponentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    course_id: UUID
    name: str
    weight: float
    is_optional: bool
    is_active: bool


class CourseAssignmentCreate(BaseModel):
    section_id: UUID
    teacher_id: UUID | None = None
    teacher_name: str | None = Field(default=None, max_length=120)


class CourseAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    course_id: UUID
    grade_id: UUID
    section_id: UUID
    teacher_id: UUID | None = None
    teacher_name: str | None = None


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str | None = None
    is_active: bool = True
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
