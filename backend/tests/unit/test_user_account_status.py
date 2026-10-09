"""Account deactivation preserves links, denies login/JWT and is auditable."""

from uuid import UUID

import pytest
from sqlalchemy import select
from test_academic_authorization import scenario, sessions

from app.api.dependencies import get_current_user
from app.core.security import hash_password
from app.endpoints import auth, users
from app.models.academic import CourseAssignment
from app.models.student import Student
from app.models.user import AuditLog, User

__all__ = ["scenario", "sessions"]


@pytest.fixture
def account_api(scenario, sessions):
    client, ids, actors, current = scenario
    client.app.include_router(users.router, prefix="/users")
    client.app.include_router(auth.router, prefix="/auth")
    with sessions() as db:
        for code in ("admin", "teacher"):
            actor = actors[code]
            actor.email = f"{code}@paideia.local"
            account = db.get(User, actor.id)
            account.email = actor.email
            account.password_hash = hash_password("Synthetic-password-2026")
        db.commit()
    current["user"] = actors["admin"]
    return client, ids, actors, current


@pytest.mark.parametrize("role", ["teacher", "student", "parent"])
def test_status_and_compatibility_delete_preserve_every_relationship(account_api, sessions, role):
    client, ids, actors, _current = account_api
    target = str(actors[role].id)
    before = client.get(f"/users/{target}").json()
    pupil_before = client.get("/students").json()
    with sessions() as db:
        assignments = [(a.id, a.teacher_id) for a in db.scalars(select(CourseAssignment))]
    assert client.delete(f"/users/{target}").status_code == 204
    inactive = client.get(f"/users/{target}").json()
    assert inactive == {**before, "is_active": False}
    assert client.get("/students").json() == pupil_before
    assert client.patch(f"/users/{target}", json={"is_active": True}).status_code == 200
    assert client.get(f"/users/{target}").json() == before
    with sessions() as db:
        assert [(a.id, a.teacher_id) for a in db.scalars(select(CourseAssignment))] == assignments
        assert db.get(User, UUID(target)) is not None
        actions = db.scalars(
            select(AuditLog).where(AuditLog.details == target).order_by(AuditLog.created_at)
        ).all()
        assert [a.action for a in actions] == ["USER_DEACTIVATED", "USER_REACTIVATED"]
        assert {a.actor_email for a in actions} == {actors["admin"].email}


def test_disabled_account_cannot_login_or_use_existing_token(account_api):
    client, _ids, actors, current = account_api
    credentials = {"email": actors["teacher"].email, "password": "Synthetic-password-2026"}
    response = client.post("/auth/login", json=credentials)
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert (
        client.patch(f"/users/{actors['teacher'].id}", json={"is_active": False}).status_code == 200
    )
    assert client.post("/auth/login", json=credentials).status_code == 401
    override = client.app.dependency_overrides.pop(get_current_user)
    assert client.get("/grades", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    client.app.dependency_overrides[get_current_user] = override
    current["user"] = actors["admin"]
    assert (
        client.patch(f"/users/{actors['teacher'].id}", json={"is_active": True}).status_code == 200
    )
    assert client.post("/auth/login", json=credentials).status_code == 200


def test_last_administrator_and_null_status_are_protected(account_api, sessions):
    client, _ids, actors, _current = account_api
    target = str(actors["admin"].id)
    assert client.delete(f"/users/{target}").status_code == 409
    assert client.patch(f"/users/{target}", json={"is_active": False}).status_code == 409
    assert client.patch(f"/users/{target}", json={"is_active": None}).status_code == 422
    with sessions() as db:
        assert db.get(User, UUID(target)).is_active
        assert db.scalar(select(AuditLog.id)) is None


def test_nonadmin_cannot_change_account_status(account_api):
    client, _ids, actors, current = account_api
    current["user"] = actors["teacher"]
    target = str(actors["student"].id)
    assert client.patch(f"/users/{target}", json={"is_active": False}).status_code == 403
    assert client.delete(f"/users/{target}").status_code == 403


def test_status_can_be_changed_even_with_archived_linked_student(account_api, sessions):
    client, ids, actors, _current = account_api
    with sessions() as db:
        db.get(Student, UUID(ids["students"][0])).status = "INACTIVE"
        db.commit()
    result = client.patch(f"/users/{actors['student'].id}", json={"is_active": False})
    assert result.status_code == 200
    assert result.json()["student_id"] == ids["students"][0]


def test_concurrent_administrator_deactivation_retains_one_active(account_api, sessions):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from uuid import uuid4

    from fastapi import HTTPException

    client, _ids, actors, _current = account_api
    with sessions() as db:
        original = db.get(User, actors["admin"].id)
        other = User(
            id=uuid4(),
            role_id=original.role_id,
            email="second@paideia.local",
            full_name="Segundo admin",
            password_hash="synthetic",
        )
        db.add(other)
        db.commit()
        other_id = other.id
        if db.bind.dialect.name != "postgresql":
            pytest.skip("Concurrent row-lock behavior requires PostgreSQL")
    barrier = Barrier(2)

    def disable(target):
        with sessions() as db:
            account = db.get(User, target)
            # Load role before synchronizing the two competing transactions.
            assert account.role.code == "admin"
            barrier.wait(timeout=10)
            try:
                users._set_account_status(db, account, False, account)
                db.commit()
                return 200
            except HTTPException as error:
                db.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(disable, [actors["admin"].id, other_id]))
    assert sorted(results) == [200, 409]
    with sessions() as db:
        assert sum(db.get(User, target).is_active for target in [actors["admin"].id, other_id]) == 1


@pytest.mark.parametrize("sessions", ["0014_evaluation_configuration_revisions"], indirect=True)
def test_account_status_migration_preserves_existing_users_and_roundtrip(sessions):
    import os
    from uuid import uuid4

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    if not os.environ.get("PAIDEIA_TEST_POSTGRES_URL"):
        pytest.skip("Requires migrated PostgreSQL")
    with sessions() as db:
        role_id, user_id = uuid4(), uuid4()
        db.execute(
            text("INSERT INTO roles (id,code,name) VALUES (:id,'admin','Admin')"), {"id": role_id}
        )
        db.execute(
            text(
                "INSERT INTO users (id,role_id,email,password_hash,full_name) "
                "VALUES (:id,:role,'migration@paideia.local','synthetic','Histórico')"
            ),
            {"id": user_id, "role": role_id},
        )
        db.commit()
        columns = "id, role_id, email, password_hash, full_name, created_at, updated_at"
        before = db.execute(text(f"SELECT {columns} FROM users")).all()
    command.upgrade(Config("alembic.ini"), "head")
    with sessions() as db:
        assert db.execute(text(f"SELECT {columns} FROM users")).all() == before
        assert db.get(User, user_id).is_active is True
    # This fixture is a UUID schema; public is never downgraded.
    command.downgrade(Config("alembic.ini"), "0014_evaluation_configuration_revisions")
    command.upgrade(Config("alembic.ini"), "head")
    with sessions() as db:
        assert db.execute(text(f"SELECT {columns} FROM users")).all() == before
