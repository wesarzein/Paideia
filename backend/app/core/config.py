from functools import cached_property
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )

    project_name: str = "Paideia"
    api_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = Field(
        default="postgresql+psycopg://paideia_user:change_me_only_for_local_dev@localhost:5432/paideia"
    )
    backend_cors_origins: str = "http://localhost:4200"
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    initial_admin_email: str | None = None
    initial_admin_password: str | None = Field(default=None, min_length=12, max_length=128)
    initial_admin_full_name: str = "Administrador"

    @model_validator(mode="after")
    def validate_deployment_settings(self) -> "Settings":
        if self.environment not in ("staging", "production"):
            return self
        if any(word in self.jwt_secret_key.lower() for word in ("replace", "change_me", "example")):
            raise ValueError("JWT_SECRET_KEY debe ser un secreto propio del entorno")
        try:
            url = make_url(self.database_url)
        except Exception:
            raise ValueError("DATABASE_URL no es válida") from None
        password = url.password or ""
        if (
            url.drivername != "postgresql+psycopg"
            or len(password) < 16
            or any(word in password.lower() for word in ("replace", "change_me"))
        ):
            raise ValueError(
                "Configure PostgreSQL con una contraseña propia de al menos 16 caracteres"
            )
        if not self.cors_origins or any(
            not origin.startswith("https://") or "*" in origin or ".invalid" in origin
            for origin in self.cors_origins
        ):
            raise ValueError("Configure una lista explícita de orígenes HTTPS para el despliegue")
        return self

    @cached_property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


settings = Settings()
