"""Existing daily attendance semantics with validated statuses and period boundaries."""

from uuid import uuid4

import pytest
from test_academic_authorization import scenario, sessions

__all__ = ["scenario", "sessions"]


def payload(ids, **changes):
    return {
        "student_id": ids["students"][0],
        "course_id": ids["courses"][0],
        "period_id": ids["period"],
        "attendance_date": "2026-04-01",
        "status": "PRESENT",
        **changes,
    }


@pytest.mark.parametrize("value", ["UNKNOWN", "", "   ", None])
def test_unknown_status_never_changes_existing_daily_record(scenario, value):
    client, ids, _actors, _current = scenario
    before = client.get("/attendance").json()
    assert client.post("/attendance", json=payload(ids, status=value)).status_code == 422
    assert client.get("/attendance").json() == before


def test_daily_retry_keeps_identity_and_existing_three_states(scenario):
    client, ids, _actors, _current = scenario
    before = client.get("/attendance").json()
    record = next(row for row in before if row["student_id"] == ids["students"][0])
    for value, expected in [("present", "PRESENT"), ("ABSENT", "ABSENT"), (" late ", "LATE")]:
        result = client.post("/attendance", json=payload(ids, status=value))
        assert result.status_code == 201, result.text
        assert result.json()["id"] == record["id"]
        assert result.json()["status"] == expected
        assert len(client.get("/attendance").json()) == len(before)


@pytest.mark.parametrize(
    "day,expected",
    [("2026-01-01", 201), ("2026-12-31", 201), ("2025-12-31", 422), ("2027-01-01", 422)],
)
def test_attendance_period_boundaries(scenario, day, expected):
    client, ids, _actors, _current = scenario
    before = client.get("/attendance").json()
    result = client.post("/attendance", json=payload(ids, attendance_date=day))
    assert result.status_code == expected, result.text
    if expected == 422:
        assert client.get("/attendance").json() == before


@pytest.mark.parametrize("field", ["student_id", "course_id", "period_id"])
def test_nonexistent_attendance_entities_are_404(scenario, field):
    client, ids, _actors, _current = scenario
    before = client.get("/attendance").json()
    assert client.post("/attendance", json=payload(ids, **{field: str(uuid4())})).status_code == 404
    assert client.get("/attendance").json() == before


def test_unassigned_course_cannot_update_existing_attendance(scenario):
    client, ids, _actors, _current = scenario
    before = client.get("/attendance").json()
    assert (
        client.post("/attendance", json=payload(ids, course_id=ids["courses"][1])).status_code
        == 403
    )
    assert client.get("/attendance").json() == before


def test_daily_retry_preserves_remarks_unless_explicitly_changed(scenario):
    client, ids, _actors, _current = scenario
    original = client.post(
        "/attendance", json=payload(ids, remarks="Observación sintética conservable")
    )
    assert original.status_code == 201
    repeated = client.post("/attendance", json=payload(ids, status="LATE"))
    assert repeated.status_code == 201
    assert repeated.json()["id"] == original.json()["id"]
    assert repeated.json()["remarks"] == original.json()["remarks"]
    cleared = client.post("/attendance", json=payload(ids, remarks=None))
    assert cleared.status_code == 201 and cleared.json()["remarks"] is None
