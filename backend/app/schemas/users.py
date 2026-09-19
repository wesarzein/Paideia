from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, TypeAdapter, field_validator


class UserCreate(BaseModel):
    email: str
    full_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    role_code: str = Field(default="teacher")

    @field_validator("email", mode="before")
    @classmethod
    def allow_local_demo_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.endswith("@paideia.local"):
            return normalized
        return str(TypeAdapter(EmailStr).validate_python(normalized))


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role_code: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: str
    created_at: datetime | None = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
