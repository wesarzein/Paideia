"""Matrix query dimensions never bypass the shared authorization scope."""

import pytest
from test_academic_authorization import scenario, sessions

__all__ = ["scenario", "sessions"]


def test_exact_evaluation_context_filters_and_authorization(scenario):
    client, ids, _actors, _current = scenario
    payload = {
        "student_id": ids["students"][0],
        "course_id": ids["courses"][0],
        "period_id": ids["period"],
        "academic_bimester": 1,
        "evaluation_block": 2,
        "evaluation_name": "Matriz explícita",
        "evaluation_type": "Cuaderno",
        "assessment_date": "2026-04-02",
        "score": 0,
    }
    created = client.post("/grades", json=payload)
    assert created.status_code == 201
    filters = {key: value for key, value in payload.items() if key != "score"}
    assert client.get("/grades", params=filters).json() == [created.json()]
    for key, value in [
        ("academic_bimester", 2),
        ("evaluation_block", 1),
        ("evaluation_name", "Otra"),
        ("assessment_date", "2026-04-01"),
        ("evaluation_type", "Módulo"),
        ("student_id", ids["students"][2]),
    ]:
        assert client.get("/grades", params={**filters, key: value}).json() == []


@pytest.mark.parametrize(
    "filters", [{"academic_bimester": 0}, {"evaluation_block": 3}, {"assessment_date": "invalid"}]
)
def test_invalid_matrix_query_context_is_422(scenario, filters):
    client, _ids, _actors, _current = scenario
    assert client.get("/grades", params=filters).status_code == 422
