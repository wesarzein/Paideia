"""Manual writes reject invalid context without changing existing historical data."""

from uuid import UUID, uuid4

import pytest
from test_academic_authorization import scenario, sessions

from app.models.academic import CourseAssessmentComponent

__all__ = ["scenario", "sessions"]


def payload(ids, **changes):
    return {
        "student_id": ids["students"][0],
        "course_id": ids["courses"][0],
        "period_id": ids["period"],
        "assessment_date": "2026-04-02",
        "evaluation_name": "Validación manual",
        "score": 0,
        **changes,
    }


@pytest.mark.parametrize("field", ["student_id", "course_id", "period_id"])
def test_missing_entities_return_404_without_writes(scenario, field):
    client, ids, _actors, _current = scenario
    before = client.get("/grades").json()
    assert client.post("/grades", json=payload(ids, **{field: str(uuid4())})).status_code == 404
    assert client.get("/grades").json() == before


@pytest.mark.parametrize("day", ["2025-12-31", "2027-01-01"])
def test_outside_period_rejected_on_create_and_patch(scenario, day):
    client, ids, _actors, _current = scenario
    before = client.get("/grades").json()
    assert client.post("/grades", json=payload(ids, assessment_date=day)).status_code == 422
    assert (
        client.patch(
            f"/grades/{before[0]['id']}", json={"assessment_date": day, "score": 1}
        ).status_code
        == 422
    )
    assert client.get("/grades").json() == before


@pytest.mark.parametrize("day", ["2026-01-01", "2026-12-31"])
def test_period_boundaries_and_real_zero_remain_valid(scenario, day):
    client, ids, _actors, _current = scenario
    response = client.post("/grades", json=payload(ids, assessment_date=day))
    assert response.status_code == 201, response.text
    original = response.json()
    edited = client.patch(f"/grades/{original['id']}", json={"score": 0, "qualitative_note": None})
    assert edited.status_code == 200
    assert edited.json()["assessment_config"] == original["assessment_config"]


@pytest.mark.parametrize(
    "changes",
    [
        {"score": None},
        {"assessment_date": None},
        {"evaluation_name": None},
        {"evaluation_type": None},
        {"evaluation_name": "   "},
    ],
)
def test_invalid_explicit_fields_are_422_not_database_errors(scenario, changes):
    client, _ids, _actors, _current = scenario
    before = client.get("/grades").json()
    assert client.patch(f"/grades/{before[0]['id']}", json=changes).status_code == 422
    assert client.get("/grades").json() == before


def test_component_validation_and_edit_of_archived_component(scenario, sessions):
    client, ids, _actors, _current = scenario
    with sessions() as db:
        components = [
            CourseAssessmentComponent(
                id=uuid4(), course_id=UUID(course), name=name, is_active=active
            )
            for course, name, active in [
                (ids["courses"][0], "Válido", True),
                (ids["courses"][0], "Archivado", False),
                (ids["courses"][1], "Otro curso", True),
            ]
        ]
        db.add_all(components)
        db.commit()
        component_ids = [str(component.id) for component in components]
    response = client.post("/grades", json=payload(ids, component_id=component_ids[0]))
    assert response.status_code == 201, response.text
    original = response.json()
    before = client.get("/grades").json()
    for invalid in [*component_ids[1:], str(uuid4())]:
        assert client.post("/grades", json=payload(ids, component_id=invalid)).status_code == 422
        assert (
            client.patch(
                f"/grades/{original['id']}", json={"component_id": invalid, "score": 20}
            ).status_code
            == 422
        )
        assert client.get("/grades").json() == before
    with sessions() as db:
        db.get(CourseAssessmentComponent, UUID(component_ids[0])).is_active = False
        db.commit()
    # Archival must not block a score correction preserving the original basis.
    edited = client.patch(f"/grades/{original['id']}", json={"score": 5})
    assert edited.status_code == 200
    assert edited.json()["assessment_config"] == original["assessment_config"]
    assert edited.json()["assessment_weight"] == original["assessment_weight"]
