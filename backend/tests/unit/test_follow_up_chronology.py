"""Authorized timeline exposes date/author without changing attribution or history."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from test_academic_authorization import scenario, sessions

from app.models.follow_up import FollowUp

__all__ = ["scenario", "sessions"]


@pytest.mark.parametrize("category", ["OBSERVATION", "PEDAGOGICAL_AGREEMENT", "MEETING", "ACTION"])
def test_created_categories_keep_date_and_author_when_edited(scenario, category):
    client, ids, actors, current = scenario
    created = client.post(
        "/follow-up",
        json={
            "student_id": ids["students"][0],
            "category": category,
            "action": "Registro sintético",
        },
    )
    assert created.status_code == 201
    item = created.json()
    assert item["recorded_by_id"] == str(actors["teacher"].id)
    assert item["recorded_by_name"] == "teacher"
    assert datetime.fromisoformat(item["created_at"])
    assert not {"email", "password_hash", "parent_user_id"} & item.keys()
    current["user"] = actors["coordinator"]
    edited = client.patch(f"/follow-up/{item['id']}", json={"action": "Descripción corregida"})
    assert edited.status_code == 200
    assert edited.json()["created_at"] == item["created_at"]
    assert edited.json()["recorded_by_id"] == item["recorded_by_id"]
    assert edited.json()["recorded_by_name"] == item["recorded_by_name"]
    assert item["id"] in {
        row["id"]
        for row in client.get("/follow-up", params={"student_id": ids["students"][0]}).json()
    }


def test_timeline_scope_and_legacy_unknown_author_are_preserved(scenario, sessions):
    client, ids, actors, current = scenario
    with sessions() as db:
        legacy = FollowUp(
            student_id=UUID(ids["students"][0]),
            recorded_by_id=None,
            action="Entrada sintética legada",
            created_at=datetime(2000, 1, 1, tzinfo=UTC),
        )
        db.add(legacy)
        db.commit()
        legacy_id = str(legacy.id)
    rows = client.get("/follow-up", params={"student_id": ids["students"][0]}).json()
    assert rows[-1]["id"] == legacy_id and rows[-1]["recorded_by_name"] is None
    assert all(row["student_id"] == ids["students"][0] for row in rows)
    assert client.get("/follow-up", params={"student_id": ids["students"][2]}).json() == []
    current["user"] = actors["parent"]
    assert client.get("/follow-up", params={"student_id": ids["students"][0]}).status_code == 403
