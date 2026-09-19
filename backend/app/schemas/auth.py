from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, TypeAdapter, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.endswith("@paideia.local"):
            return normalized
        return str(TypeAdapter(EmailStr).validate_python(normalized))


class UserSession(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSession
