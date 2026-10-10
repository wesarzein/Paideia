from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GradeLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def trimmed(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El nombre no puede estar vacío")
        return value.strip()


class GradeCreate(GradeLabel):
    level: str = Field(min_length=1, max_length=80)


class GradeResponse(GradeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool


class SectionLabel(GradeLabel):
    name: str = Field(min_length=1, max_length=20)


class SectionCreate(SectionLabel):
    grade_id: UUID


class SectionResponse(SectionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool
