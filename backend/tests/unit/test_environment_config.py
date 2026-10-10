"""Deployment configuration must fail safely without using a database."""

import os

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.seed_dev import ensure_development_target


def production(**overrides):
    values = {
        "environment": "production",
        "jwt_secret_key": "a" * 64,
        "database_url": "postgresql+psycopg://service:uniquepassword0123456789@postgres/paideia",
        "backend_cors_origins": "https://school.test",
    }
    return Settings(_env_file=None, **(values | overrides))


@pytest.mark.parametrize(
    "overrides",
    [
        {"jwt_secret_key": "replace_with_a_secure_local_secret"},
        {"database_url": "sqlite://"},
        {"database_url": "postgresql+psycopg://service:change_me_only_for_local_dev@postgres/db"},
        {"backend_cors_origins": "*"},
        {"backend_cors_origins": "http://school.test"},
        {"backend_cors_origins": "https://school.example.invalid"},
    ],
)
def test_production_rejects_unsafe_configuration(overrides):
    with pytest.raises(ValidationError):
        production(**overrides)


def test_valid_production_settings():
    assert production().cors_origins == ["https://school.test"]


def test_synthetic_seed_rejects_institutional_database(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(
        settings, "database_url", "postgresql+psycopg://paideia_user@postgres/paideia"
    )
    monkeypatch.setenv("ALLOW_SYNTHETIC_SEED", "true")
    with pytest.raises(RuntimeError):
        ensure_development_target()


def test_synthetic_seed_requires_explicit_opt_in(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(
        settings, "database_url", "postgresql+psycopg://paideia_dev@postgres/paideia_dev_test"
    )
    monkeypatch.delenv("ALLOW_SYNTHETIC_SEED", raising=False)
    assert "ALLOW_SYNTHETIC_SEED" not in os.environ
    with pytest.raises(RuntimeError):
        ensure_development_target()
