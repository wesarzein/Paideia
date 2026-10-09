"""Calendar administration, authorization and protection of existing synthetic history."""

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_academic_authorization import scenario, sessions

from app.endpoints import periods
from app.models.academic import AcademicPeriod

__all__ = ["scenario", "sessions"]


@pytest.fixture
def period_api(scenario):
    client, ids, actors, current = scenario
    client.app.include_router(periods.router, prefix="/academic/periods")
    for role, actor in actors.items():
        actor.email = f"{role}@synthetic.invalid"
    current["user"] = actors["admin"]
    return client, ids, actors, current


def payload(**changes):
    return {
        "name": "Calendario sintético 2027",
        "starts_on": "2027-01-01",
        "ends_on": "2027-12-31",
        **changes,
    }


def test_create_edit_and_catalog_include_other_years_without_changing_history(period_api):
    client, ids, _actors, _current = period_api
    before = client.get("/grades").json()
    created = client.post("/academic/periods", json=payload())
    assert created.status_code == 201, created.text
    period = created.json()
    assert {row["id"] for row in client.get("/academic/catalog").json()["periods"]} == {
        ids["period"],
        period["id"],
    }
    edited = client.patch(
        f"/academic/periods/{period['id']}",
        json={"name": "Calendario editado 2027", "starts_on": "2027-02-01"},
    )
    assert edited.status_code == 200
    assert edited.json()["id"] == period["id"]
    assert edited.json()["starts_on"] == "2027-02-01"
    assert client.get("/grades").json() == before


@pytest.mark.parametrize("role", ["teacher", "coordinator", "director", "student", "parent"])
def test_read_only_roles_cannot_manage_calendars(period_api, role):
    client, ids, actors, current = period_api
    current["user"] = actors[role]
    assert client.get("/academic/periods").status_code == 200
    assert client.post("/academic/periods", json=payload()).status_code == 403
    assert (
        client.patch(f"/academic/periods/{ids['period']}", json={"name": "Ajeno"}).status_code
        == 403
    )


@pytest.mark.parametrize(
    "changes", [{"starts_on": "2028-01-01"}, {"name": "   "}, {"ends_on": None}]
)
def test_invalid_period_creation_rejected_without_adding_rows(period_api, changes):
    client, _ids, _actors, _current = period_api
    before = client.get("/academic/periods").json()
    assert client.post("/academic/periods", json=payload(**changes)).status_code == 422
    assert client.get("/academic/periods").json() == before


def test_duplicate_name_null_and_missing_period_are_consistent_errors(period_api):
    client, ids, _actors, _current = period_api
    assert client.post("/academic/periods", json=payload()).status_code == 201
    assert (
        client.post(
            "/academic/periods", json=payload(name=" calendario sintético 2027 ")
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/academic/periods/{ids['period']}", json={"name": "Calendario sintético 2027"}
        ).status_code
        == 409
    )
    assert (
        client.patch(f"/academic/periods/{ids['period']}", json={"ends_on": None}).status_code
        == 422
    )
    assert (
        client.patch(f"/academic/periods/{uuid4()}", json={"name": "No existe"}).status_code == 404
    )


def test_period_dates_cannot_exclude_existing_grades(period_api):
    client, ids, _actors, _current = period_api
    before = client.get("/academic/periods").json()
    grades = client.get("/grades").json()
    assert (
        client.patch(
            f"/academic/periods/{ids['period']}", json={"starts_on": "2026-04-02"}
        ).status_code
        == 422
    )
    assert client.get("/academic/periods").json() == before
    assert client.get("/grades").json() == grades


def test_period_dates_cannot_exclude_attendance_without_any_grades(period_api):
    client, ids, _actors, _current = period_api
    period = client.post("/academic/periods", json=payload()).json()
    created = client.post(
        "/attendance",
        json={
            "student_id": ids["students"][0],
            "course_id": ids["courses"][0],
            "period_id": period["id"],
            "attendance_date": "2027-04-01",
            "status": "PRESENT",
        },
    )
    assert created.status_code == 201
    before = client.get("/attendance").json()
    assert (
        client.patch(
            f"/academic/periods/{period['id']}", json={"ends_on": "2027-03-31"}
        ).status_code
        == 422
    )
    assert client.get("/attendance").json() == before


def test_concurrent_period_creation_has_only_one_winner(period_api, sessions):
    if not os.environ.get("PAIDEIA_TEST_POSTGRES_URL"):
        pytest.skip("Advisory lock behavior requires PostgreSQL")
    client, _ids, _actors, _current = period_api
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: client.post("/academic/periods", json=payload()).status_code, range(2)
            )
        )
    assert sorted(results) == [201, 409]
    with sessions() as db:
        assert (
            len(
                db.scalars(
                    select(AcademicPeriod).where(AcademicPeriod.name == payload()["name"])
                ).all()
            )
            == 1
        )


def test_period_edit_waits_for_concurrent_grade_and_preserves_its_date(period_api, sessions):
    if not os.environ.get("PAIDEIA_TEST_POSTGRES_URL"):
        pytest.skip("Row-lock behavior requires PostgreSQL")
    from datetime import date
    from threading import Event
    from uuid import UUID

    from sqlalchemy import event

    from app.models.academic import GradeRecord

    client, ids, _actors, _current = period_api
    period = client.post("/academic/periods", json=payload()).json()
    editing = Event()
    db = sessions()
    engine = db.bind

    def waiting_for_calendar(_conn, _cursor, statement, _parameters, _context, _executemany):
        if "FOR UPDATE" in statement:
            editing.set()

    event.listen(engine, "before_cursor_execute", waiting_for_calendar)
    try:
        db.get(AcademicPeriod, UUID(period["id"]), with_for_update={"read": True})
        # Same shared calendar lock held by grade POST/PATCH and Excel confirmation.
        record = GradeRecord(
            student_id=UUID(ids["students"][0]),
            course_id=UUID(ids["courses"][0]),
            period_id=UUID(period["id"]),
            assessment_date=date(2027, 6, 1),
            evaluation_name="Nota concurrente",
            score=10,
        )
        db.add(record)
        db.flush()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                client.patch, f"/academic/periods/{period['id']}", json={"starts_on": "2027-06-02"}
            )
            if not editing.wait(timeout=10):
                db.rollback()
                pytest.fail("Period edit never reached its row lock")
            db.commit()
            assert future.result(timeout=10).status_code == 422
        assert db.get(AcademicPeriod, UUID(period["id"])).starts_on == date(2027, 1, 1)
        assert db.get(GradeRecord, record.id).assessment_date == date(2027, 6, 1)
    finally:
        db.close()
        event.remove(engine, "before_cursor_execute", waiting_for_calendar)
