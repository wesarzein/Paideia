from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from test_academic_authorization import scenario, sessions

from app.endpoints.academic_history import router
from app.models.academic import GradeRecord
from app.models.academic_history import AcademicChangeHistory

__all__ = ["scenario", "sessions"]


def history(scenario, student=None):
    client, ids, _, _ = scenario
    if not getattr(client.app.state, "history_added", False):
        client.app.include_router(router, prefix="/academic")
        client.app.state.history_added = True
    return client.get("/academic/history", params={"student_id": student or ids["students"][0]})


def pg_only(sessions):
    with sessions() as db:
        if db.bind.dialect.name != "postgresql":
            pytest.skip("Database trigger acceptance requires isolated PostgreSQL")


def test_before_after_actor_delete_and_snapshot_preservation(scenario, sessions):
    pg_only(sessions)
    client, _, actors, current = scenario
    current["user"] = actors["admin"]
    record = client.get("/grades").json()[0]
    assert client.patch(f"/grades/{record['id']}", json={"score": 0}).status_code == 200
    rows = history(scenario, record["student_id"]).json()
    change = next(r for r in rows if r["record_id"] == record["id"] and r["operation"] == "UPDATE")
    assert change["before"]["score"] == record["score"]
    assert change["after"]["score"] == 0
    assert change["before"]["assessment_config"] == change["after"]["assessment_config"]
    assert change["actor_id"] == str(actors["admin"].id)
    assert change["actor_role"] == "admin" and change["source"] == "authenticated_api"
    assert change["authorization"]["method"] == "PATCH"
    assert change["authorization"]["path"] == f"/grades/{record['id']}"
    assert "admin" in change["authorization"]["allowed_roles"]
    assert change["created_at"]
    assert client.delete(f"/grades/{record['id']}").status_code == 204
    deletion = next(
        r
        for r in history(scenario, record["student_id"]).json()
        if r["record_id"] == record["id"] and r["operation"] == "DELETE"
    )
    assert deletion["before"]["score"] == 0 and deletion["after"] is None
    assert deletion["before"]["assessment_config"] == record["assessment_config"]


def test_authorization_and_rollback_do_not_write_history(scenario, sessions):
    pg_only(sessions)
    client, ids, actors, current = scenario
    current["user"] = actors["admin"]
    records = client.get("/grades").json()
    crossed = next(
        r
        for r in records
        if r["student_id"] == ids["students"][0] and r["course_id"] == ids["courses"][1]
    )
    with sessions() as db:
        initial = len(db.scalars(select(AcademicChangeHistory)).all())
    current["user"] = actors["teacher"]
    assert client.patch(f"/grades/{crossed['id']}", json={"score": 1}).status_code == 403
    assert all(r["record_id"] != crossed["id"] for r in history(scenario).json())
    assert history(scenario, ids["students"][2]).status_code == 403
    current["user"] = actors["parent"]
    assert history(scenario).status_code == 403
    with sessions() as db:
        row = db.get(GradeRecord, UUID(crossed["id"]))
        row.score = 2
        db.flush()
        db.rollback()
    with sessions() as db:
        assert len(db.scalars(select(AcademicChangeHistory)).all()) == initial


def test_attendance_followup_and_append_only_guard(scenario, sessions):
    pg_only(sessions)
    client, ids, actors, current = scenario
    current["user"] = actors["admin"]
    assert (
        client.post(
            "/attendance",
            json={
                "student_id": ids["students"][0],
                "course_id": ids["courses"][0],
                "period_id": ids["period"],
                "attendance_date": "2026-04-01",
                "status": "LATE",
            },
        ).status_code
        == 201
    )
    assert (
        client.patch(
            "/follow-up/" + ids["followups"][0], json={"action": "Cambio ficticio"}
        ).status_code
        == 200
    )
    rows = history(scenario).json()
    assert any(
        r["entity"] == "attendance_records"
        and r["before"]["status"] == "PRESENT"
        and r["after"]["status"] == "LATE"
        for r in rows
        if r["operation"] == "UPDATE"
    )
    assert any(
        r["entity"] == "follow_ups" and r["after"]["action"] == "Cambio ficticio"
        for r in rows
        if r["operation"] == "UPDATE"
    )
    for sql in (
        "DELETE FROM academic_change_history",
        "UPDATE academic_change_history SET source='changed'",
        "TRUNCATE academic_change_history",
    ):
        with sessions() as db, pytest.raises(DBAPIError):
            db.execute(text(sql))
            db.commit()
