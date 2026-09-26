from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GradeCreate(BaseModel):
    student_id: UUID
    course_id: UUID
    period_id: UUID
    evaluation_name: str = Field(default="Evaluación", min_length=1, max_length=120)
    evaluation_type: str = Field(default="Tarea", min_length=1, max_length=50)
    assessment_date: date = Field(default_factory=date.today)
    score: float = Field(ge=0, le=20)
    qualitative_note: str | None = Field(default=None, max_length=255)


class GradeUpdate(BaseModel):
    evaluation_name: str | None = Field(default=None, min_length=1, max_length=120)
    evaluation_type: str | None = Field(default=None, min_length=1, max_length=50)
    assessment_date: date | None = None
    score: float | None = Field(default=None, ge=0, le=20)
    qualitative_note: str | None = Field(default=None, max_length=255)


class GradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    course_id: UUID
    period_id: UUID
    evaluation_name: str
    evaluation_type: str
    assessment_date: date
    score: float
    qualitative_note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GradeSummary(BaseModel):
    student_id: UUID
    average: float
    count: int
