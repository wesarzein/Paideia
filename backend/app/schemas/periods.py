from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PeriodCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def chronological_dates(self):
        if self.starts_on > self.ends_on:
            raise ValueError("El inicio no puede ser posterior al fin")
        return self


class PeriodUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    starts_on: date | None = None
    ends_on: date | None = None


class PeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    starts_on: date
    ends_on: date
    created_at: datetime | None = None
