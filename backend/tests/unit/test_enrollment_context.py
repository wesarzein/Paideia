"""Scoped enrollment filters and concurrent academic registration, without deletion."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from test_academic_authorization import scenario, sessions

__all__ = ["scenario", "sessions"]


def payload(ids, **changes):
    return {
        "student_id": ids["students"][2],
        "course_id": ids["courses"][1],
        "period_id": ids["period"],
        **changes,
    }


def test_filtered_enrollments_remain_within_teacher_scope(scenario):
    client, ids, _actors, _current = scenario
    rows = client.get("/enrollments").json()
    assert rows
    for row in rows:
        result = client.get(
            "/enrollments",
            params={
                "student_id": row["student_id"],
                "course_id": row["course_id"],
                "period_id": row["period_id"],
            },
        )
        assert result.status_code == 200 and result.json() == [row]
    assert client.get("/enrollments", params={"student_id": ids["students"][2]}).json() == []
    assert (
        client.get(
            "/enrollments",
            params={"course_id": ids["courses"][1], "student_id": ids["students"][0]},
        ).json()
        == []
    )


@pytest.mark.parametrize("field", ["student_id", "course_id", "period_id"])
def test_enrollment_missing_context_is_rejected_without_writes(scenario, field):
    client, ids, actors, current = scenario
    current["user"] = actors["admin"]
    before = client.get("/enrollments").json()
    assert (
        client.post("/enrollments", json=payload(ids, **{field: str(uuid4())})).status_code == 404
    )
    assert client.get("/enrollments").json() == before


def test_active_enrollment_and_duplicate_preserve_identity(scenario):
    client, ids, actors, current = scenario
    current["user"] = actors["admin"]
    result = client.post("/enrollments", json=payload(ids, status=" active "))
    assert result.status_code == 201 and result.json()["status"] == "ACTIVE"
    created = result.json()
    assert client.post("/enrollments", json=payload(ids)).status_code == 409
    assert client.get(
        "/enrollments", params={"student_id": ids["students"][2], "course_id": ids["courses"][1]}
    ).json() == [created]


@pytest.mark.parametrize("value", ["   ", None])
def test_blank_or_null_state_cannot_create_or_change_an_enrollment(scenario, value):
    client, ids, actors, current = scenario
    current["user"] = actors["admin"]
    before = client.get("/enrollments").json()
    assert client.post("/enrollments", json=payload(ids, status=value)).status_code == 422
    assert (
        client.patch(f"/enrollments/{ids['enrollments'][0]}", json={"status": value}).status_code
        == 422
    )
    assert client.get("/enrollments").json() == before


def test_concurrent_registration_has_one_winner(scenario):
    if not os.environ.get("PAIDEIA_TEST_POSTGRES_URL"):
        pytest.skip("Enrollment locking requires PostgreSQL")
    client, ids, actors, current = scenario
    current["user"] = actors["admin"]
    start = Barrier(2)

    def save(_):
        start.wait(timeout=10)
        return client.post("/enrollments", json=payload(ids)).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(save, range(2)))
    assert sorted(results) == [201, 409]
    assert (
        len(
            client.get(
                "/enrollments",
                params={"student_id": ids["students"][2], "course_id": ids["courses"][1]},
            ).json()
        )
        == 1
    )
