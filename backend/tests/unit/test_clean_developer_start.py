"""Fresh UUID schema: real synthetic file, full startup, login and second startup."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from test_roster_persistence import sessions

from app.core.database import get_db
from app.models.academic import GradeRecord
from app.models.student import Student

__all__ = ["sessions"]


def test_fresh_seed_start_login_and_restart_preserve_catalog(sessions, monkeypatch):
    from app import main, seed_dev
    from app.core.config import settings

    with sessions() as db:
        if db.bind.dialect.name != "postgresql":
            pytest.skip("Clean installation acceptance requires PostgreSQL")
        assert db.scalar(text("SELECT current_schema()")).startswith("phase2_")
        assert db.scalar(select(Student)) is None
    fixture = Path("/fixtures/roster.synthetic.json")
    assert fixture.exists(), "Mount the tracked synthetic fixture, never a private roster"
    source = json.loads(fixture.read_text(encoding="utf-8"))
    expected = sum(len(section["students"]) for section in source["sections"])
    # The UUID fixture already guards the real target; CI uses a deliberately distinct
    # disposable database/user that the normal developer seed correctly refuses.
    from sqlalchemy.engine import make_url

    if make_url(settings.database_url).username != "paideia_dev":
        monkeypatch.setattr(seed_dev, "ensure_development_target", lambda: None)
    else:
        seed_dev.ensure_development_target()
    monkeypatch.setattr(seed_dev, "SessionLocal", sessions)
    seed_dev.main()
    monkeypatch.setattr(main, "SessionLocal", sessions)
    monkeypatch.setattr(settings, "initial_admin_email", "fresh@paideia-dev.example.com")
    monkeypatch.setattr(settings, "initial_admin_password", "Synthetic-new-clone-password")
    app = main.create_app()

    def database():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = database
    for _ in range(2):
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={
                    "email": settings.initial_admin_email,
                    "password": settings.initial_admin_password,
                },
            )
            assert login.status_code == 200
            headers = {"Authorization": "Bearer " + login.json()["access_token"]}
            students = client.get("/api/v1/students", headers=headers)
            assert students.status_code == 200 and len(students.json()) == expected
            assert client.get("/api/v1/kpis", headers=headers).status_code == 200
            assert (
                client.get("/api/v1/risk-models", headers=headers).json()["active_run_id"] is None
            )
    with sessions() as db:
        assert db.scalar(select(GradeRecord)) is None
