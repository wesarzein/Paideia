from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GradeCreate(BaseModel):
    student_id: UUID
    course_id: UUID
    period_id: UUID
    score: float = Field(ge=0, le=20)
    qualitative_note: str | None = Field(default=None, max_length=255)


class GradeUpdate(BaseModel):
    score: float | None = Field(default=None, ge=0, le=20)
    qualitative_note: str | None = Field(default=None, max_length=255)


class GradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    course_id: UUID
    period_id: UUID
    score: float
    qualitative_note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GradeSummary(BaseModel):
    student_id: UUID
    average: float
    count: int
