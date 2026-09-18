from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "Paideia"
    api_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    database_url: str = Field(
        default="postgresql+psycopg://paideia_user:change_me_only_for_local_dev@localhost:5432/paideia"
    )
    backend_cors_origins: str = "http://localhost:4200"
    jwt_secret_key: str = "replace_with_a_secure_local_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    @cached_property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


settings = Settings()
