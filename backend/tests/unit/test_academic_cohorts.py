"""Guarded synthetic catalog administration preserves roster identity and history."""

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_academic_authorization import scenario, sessions

from app.endpoints import cohorts
from app.models.user import AuditLog

__all__ = ["scenario", "sessions"]


@pytest.fixture
def cohort_api(scenario):
    client, ids, actors, current = scenario
    client.app.include_router(cohorts.router, prefix="/academic")
    for role, actor in actors.items():
        actor.email = f"{role}@synthetic.invalid"
    current["user"] = actors["admin"]
    return client, ids, actors, current


def new_grade(client):
    reply = client.post("/academic/grades", json={"name": "2°", "level": " primaria "})
    assert reply.status_code == 201, reply.text
    return reply.json()


def test_create_rename_preserves_roster_codes_references_and_history(cohort_api, sessions):
    client, ids, _actors, _current = cohort_api
    before = client.get("/students").json()
    notes = client.get("/grades").json()
    grade = client.get("/academic/grades").json()[0]
    renamed = client.patch(f"/academic/grades/{grade['id']}", json={"name": "1° grado"})
    assert renamed.status_code == 200 and renamed.json()["id"] == grade["id"]
    assert client.get("/students").json() == before
    assert client.get("/grades").json() == notes
    assert any(g["name"] == "1° grado" for g in client.get("/academic/catalog").json()["grades"])
    created = new_grade(client)
    section = client.post("/academic/sections", json={"grade_id": created["id"], "name": " azul "})
    assert section.status_code == 201 and section.json()["name"] == "AZUL"
    changed = client.patch(f"/academic/sections/{section.json()['id']}", json={"name": "verde"})
    assert changed.status_code == 200 and changed.json()["grade_id"] == created["id"]
    with sessions() as db:
        assert {a.action for a in db.scalars(select(AuditLog)).all()} >= {
            "GRADE_CREATED",
            "GRADE_LABEL_UPDATED",
            "SECTION_CREATED",
            "SECTION_LABEL_UPDATED",
        }


@pytest.mark.parametrize("role", ["teacher", "coordinator", "director", "student", "parent"])
def test_catalog_administration_denied_to_nonadmin(cohort_api, role):
    client, _ids, actors, current = cohort_api
    current["user"] = actors[role]
    for path in ["/academic/grades", "/academic/sections"]:
        assert client.get(path).status_code == 403
    assert (
        client.post("/academic/grades", json={"name": "2°", "level": "Primaria"}).status_code == 403
    )
    assert client.patch(f"/academic/grades/{uuid4()}", json={"name": "1° grado"}).status_code == 403
    assert (
        client.post("/academic/sections", json={"grade_id": str(uuid4()), "name": "A"}).status_code
        == 403
    )
    assert client.patch(f"/academic/sections/{uuid4()}", json={"name": "A"}).status_code == 403


def test_invalid_prefix_duplicates_missing_and_forbidden_changes(cohort_api):
    client, _ids, _actors, _current = cohort_api
    grade = client.get("/academic/grades").json()[0]
    before = client.get("/academic/catalog").json()
    for name, level in [("Sin número", "Primaria"), ("2°", "Otro"), ("   ", "Primaria")]:
        assert (
            client.post("/academic/grades", json={"name": name, "level": level}).status_code == 422
        )
    assert (
        client.post(
            "/academic/grades", json={"name": "1° distinto", "level": grade["level"]}
        ).status_code
        == 409
    )
    assert client.patch(f"/academic/grades/{grade['id']}", json={"name": "2°"}).status_code == 409
    assert client.patch(f"/academic/grades/{grade['id']}", json={"name": None}).status_code == 422
    assert (
        client.patch(
            f"/academic/grades/{grade['id']}", json={"name": "1°", "level": "Primaria"}
        ).status_code
        == 422
    )
    section = client.get("/academic/sections").json()[0]
    assert (
        client.patch(f"/academic/sections/{section['id']}", json={"name": "Z"}).status_code == 409
    )
    assert (
        client.post("/academic/sections", json={"grade_id": grade["id"], "name": "AA"}).status_code
        == 422
    )
    assert (
        client.post(
            "/academic/sections", json={"grade_id": grade["id"], "name": section["name"].lower()}
        ).status_code
        == 409
    )
    assert (
        client.post("/academic/sections", json={"grade_id": str(uuid4()), "name": "A"}).status_code
        == 404
    )
    assert client.patch(f"/academic/sections/{uuid4()}", json={"name": "A"}).status_code == 404
    assert client.get("/academic/catalog").json() == before


def test_new_catalog_is_usable_by_existing_student_code_generation(cohort_api):
    client, _ids, _actors, _current = cohort_api
    grade = new_grade(client)
    section = client.post("/academic/sections", json={"grade_id": grade["id"], "name": "A"}).json()
    reply = client.post(
        "/students",
        json={
            "first_name": "Alumno sintético",
            "last_name": "Prueba catálogo",
            "grade_id": grade["id"],
            "section_id": section["id"],
        },
    )
    assert reply.status_code == 201, reply.text
    assert reply.json()["student_code"] == "2P001"
    original = reply.json()
    assert (
        client.patch(
            f"/academic/grades/{grade['id']}", json={"name": "2° grado editado"}
        ).status_code
        == 200
    )
    assert (
        next(row for row in client.get("/students").json() if row["id"] == original["id"])
        == original
    )


def test_concurrent_creation_has_one_grade_and_section_winner(cohort_api):
    if not os.environ.get("PAIDEIA_TEST_POSTGRES_URL"):
        pytest.skip("Catalog locking requires PostgreSQL")
    client, _ids, _actors, _current = cohort_api
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: client.post("/academic/grades", json={"name": "2°", "level": "Primaria"}),
                range(2),
            )
        )
    assert sorted(reply.status_code for reply in results) == [201, 409]
    grade = next(reply.json() for reply in results if reply.status_code == 201)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: client.post(
                    "/academic/sections", json={"grade_id": grade["id"], "name": "A"}
                ).status_code,
                range(2),
            )
        )
    assert sorted(results) == [201, 409]
