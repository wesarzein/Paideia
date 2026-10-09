from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.services.evidence_types import EVIDENCE_TYPES, EvidenceTypeModel, normalize_evidence_type


class GradeCreate(BaseModel):
    student_id: UUID
    course_id: UUID
    period_id: UUID
    component_id: UUID | None = None
    academic_bimester: int | None = Field(default=None, ge=1)
    evaluation_block: int | None = Field(default=None, ge=1, le=2)
    evaluation_criterion_key: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,63}$")
    evaluation_name: str = Field(default="Evaluación", min_length=1, max_length=120)
    evaluation_type: str = Field(default=EVIDENCE_TYPES[0], min_length=1, max_length=50)
    assessment_date: date = Field(default_factory=date.today)
    score: float = Field(ge=0, le=20)
    qualitative_note: str | None = Field(default=None, max_length=255)

    @field_validator("evaluation_name", "evaluation_type", mode="after")
    @classmethod
    def nonblank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("La evaluación no puede estar vacía")
        return value

    @field_validator("evaluation_type", mode="before")
    @classmethod
    def validate_evaluation_type(cls, value: str, info: ValidationInfo) -> str:
        if info.data.get("evaluation_criterion_key"):
            return str(value).strip()
        return normalize_evidence_type(value)


class GradeUpdate(EvidenceTypeModel):
    component_id: UUID | None = None
    evaluation_name: str | None = Field(default=None, min_length=1, max_length=120)
    evaluation_type: str | None = Field(default=None, min_length=1, max_length=50)
    assessment_date: date | None = None
    score: float | None = Field(default=None, ge=0, le=20)
    qualitative_note: str | None = Field(default=None, max_length=255)

    @field_validator("score", "assessment_date", "evaluation_name", "evaluation_type")
    @classmethod
    def required_when_supplied(cls, value):
        if value is None:
            raise ValueError("El campo no admite null")
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("La evaluación no puede estar vacía")
        return value


class GradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    course_id: UUID
    period_id: UUID
    component_id: UUID | None = None
    academic_bimester: int | None = None
    evaluation_block: int | None = None
    evaluation_criterion_key: str | None = None
    evaluation_name: str
    evaluation_type: str
    assessment_date: date
    score: float
    assessment_weight: float
    assessment_config: dict
    evaluation_revision_id: UUID | None = None
    qualitative_note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GradeSummary(BaseModel):
    student_id: UUID
    average: float | None
    count: int
