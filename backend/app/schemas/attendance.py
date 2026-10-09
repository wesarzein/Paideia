from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AttendanceCreate(BaseModel):
    student_id: UUID
    course_id: UUID
    period_id: UUID
    attendance_date: date
    status: str = Field(default="PRESENT", min_length=1, max_length=30)
    remarks: str | None = Field(default=None, max_length=255)

    @field_validator("status")
    @classmethod
    def supported_status(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"PRESENT", "ABSENT", "LATE"}:
            raise ValueError("Estado permitido: PRESENT, ABSENT o LATE")
        return value


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    course_id: UUID
    period_id: UUID
    attendance_date: date
    status: str
    remarks: str | None = None
    created_at: datetime | None = None
