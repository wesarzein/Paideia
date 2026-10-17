from datetime import date
from types import SimpleNamespace as Row
from uuid import UUID

import pytest
from sqlalchemy import select
from test_academic_authorization import scenario, sessions

from app.endpoints.performance_forecast import router
from app.models.academic import GradeRecord
from app.services.performance_forecast import (
    load_model,
    observed_history,
    project,
    synthetic_examples,
)

__all__ = ["scenario", "sessions"]


def test_synthetic_split_is_temporal_and_disjoint_and_model_beats_baseline():
    dataset = synthetic_examples(pupils=20)
    for rows in dataset.values():
        sets = [
            {r["student"] for r in rows if r["split"] == s} for s in ("train", "validation", "test")
        ]
        assert not sets[0] & sets[1] and not sets[0] & sets[2] and not sets[1] & sets[2]
        indices = [
            [r["target_index"] for r in rows if r["split"] == s]
            for s in ("train", "validation", "test")
        ]
        assert max(indices[0]) < min(indices[1]) < min(indices[2])
    for artifact in load_model()["horizons"].values():
        assert artifact["metrics"]["mae"] < artifact["metrics"]["baseline_mae"]


def test_history_preserves_zero_and_weights_and_excludes_future_and_undated_exams():
    period = Row(id="p", name="2026", starts_on=date(2026, 1, 1), ends_on=date(2026, 12, 31))
    rows = [
        Row(
            period_id="p",
            record_kind="evaluation",
            academic_bimester=1,
            assessment_date=date(2026, 2, 1),
            score=s,
            assessment_weight=w,
        )
        for s, w in [(0, 3), (20, 1)]
    ]
    rows += [
        Row(
            period_id="p",
            record_kind="historical_bimester",
            academic_bimester=2,
            assessment_date=None,
            score=10,
            assessment_weight=1,
        ),
        Row(
            period_id="p",
            record_kind="evaluation",
            academic_bimester=3,
            assessment_date=date(2026, 8, 1),
            score=20,
            assessment_weight=1,
        ),
    ]
    history, excluded = observed_history(rows, [period], "exam", date(2026, 7, 1))
    assert history[0]["score"] == 5 and excluded == 2
    history, excluded = observed_history(rows, [period], "bimester", date(2026, 7, 1), 2, "p")
    assert [r["score"] for r in history] == [5, 10] and excluded == 1
    history, _ = observed_history(rows, [period], "bimester", date(2026, 12, 31), 1, "p")
    assert len(history) == 1


def test_insufficient_history_is_not_zero_and_predictions_are_bounded():
    model = load_model()
    assert project([], [], "exam", model)["score"] is None
    for scores in ([0, 0, 0], [20, 20, 20], [16, 12, 8]):
        pred = project([{"score": s} for s in scores], [], "exam", model)
        assert 0 <= pred["range"][0] <= pred["score"] <= pred["range"][1] <= 20
        assert pred["status"] == "experimental"


def client_for(scenario, role="coordinator"):
    client, ids, actors, current = scenario
    current["user"] = actors[role]
    if not getattr(client.app.state, "forecast_added", False):
        client.app.include_router(router, prefix="/academic-ai")
        client.app.state.forecast_added = True
    return client, ids


@pytest.mark.parametrize("role", ["student", "parent"])
def test_family_cannot_access_forecasts(scenario, role):
    client, ids = client_for(scenario, role)
    assert (
        client.get(
            "/academic-ai/forecast",
            params={"period_id": ids["period"], "student_id": ids["students"][0]},
        ).status_code
        == 403
    )


def test_teacher_scope_correlates_course_and_classroom(scenario):
    client, ids = client_for(scenario, "teacher")
    response = client.get(
        "/academic-ai/forecast",
        params={
            "period_id": ids["period"],
            "student_id": ids["students"][0],
            "as_of": "2026-07-01",
        },
    )
    assert response.status_code == 200
    assert {r["course_id"] for r in response.json()["rows"]} == {ids["courses"][0]}
    assert (
        client.get(
            "/academic-ai/forecast",
            params={"period_id": ids["period"], "student_id": ids["students"][2]},
        ).status_code
        == 404
    )


def test_forecast_reads_registered_grades_and_never_writes_them(scenario, sessions):
    client, ids = client_for(scenario)
    with sessions() as db:
        for month, score in [(2, 14), (3, 10), (12, 20)]:
            db.add(
                GradeRecord(
                    student_id=UUID(ids["students"][0]),
                    course_id=UUID(ids["courses"][0]),
                    period_id=UUID(ids["period"]),
                    assessment_date=date(2026, month, 1),
                    evaluation_name=f"Synthetic {month}",
                    score=score,
                )
            )
        db.commit()
        before = [
            (str(r.id), r.score, r.assessment_config)
            for r in db.scalars(select(GradeRecord).order_by(GradeRecord.id))
        ]
    response = client.get(
        "/academic-ai/forecast",
        params={
            "period_id": ids["period"],
            "section_id": ids["sections"][0],
            "course_id": ids["courses"][0],
            "as_of": "2026-07-01",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["predicted"] == 1
    assert data["rows"][0]["prediction"]["trend"] == "stable"
    assert len(data["rows"][0]["history"]) == 3
    assert data["rows"][0]["excluded_records"] == 1
    assert data["training_source"] == "synthetic"
    with sessions() as db:
        assert before == [
            (str(r.id), r.score, r.assessment_config)
            for r in db.scalars(select(GradeRecord).order_by(GradeRecord.id))
        ]


def test_invalid_filters_and_missing_history_are_explicit(scenario):
    client, ids = client_for(scenario)
    base = {"period_id": ids["period"], "student_id": ids["students"][0]}
    assert (
        client.get("/academic-ai/forecast", params={"period_id": ids["period"]}).status_code == 422
    )
    assert (
        client.get("/academic-ai/forecast", params={**base, "horizon": "bimester"}).status_code
        == 422
    )
    assert (
        client.get("/academic-ai/forecast", params={**base, "as_of": "2099-01-01"}).status_code
        == 422
    )
    response = client.get("/academic-ai/forecast", params=base)
    assert response.status_code == 200
    assert all(r["prediction"]["score"] is None for r in response.json()["rows"])


def test_bimester_forecast_uses_native_historical_records_without_fabricated_dates(
    scenario, sessions
):
    client, ids = client_for(scenario)
    with sessions() as db:
        for bimester, score in [(1, 14), (2, 11), (3, 8), (4, 20)]:
            db.add(
                GradeRecord(
                    student_id=UUID(ids["students"][0]),
                    course_id=UUID(ids["courses"][0]),
                    period_id=UUID(ids["period"]),
                    record_kind="historical_bimester",
                    assessment_date=None,
                    academic_bimester=bimester,
                    evaluation_block=1,
                    evaluation_name=f"Synthetic bimester {bimester}",
                    score=score,
                )
            )
        db.commit()
    response = client.get(
        "/academic-ai/forecast",
        params={
            "period_id": ids["period"],
            "student_id": ids["students"][0],
            "course_id": ids["courses"][0],
            "horizon": "bimester",
            "through_bimester": 3,
            "as_of": "2026-10-01",
        },
    )
    assert response.status_code == 200
    row = response.json()["rows"][0]
    assert [h["score"] for h in row["history"]] == [14, 11, 8]
    assert row["prediction"]["status"] == "experimental"
    assert row["prediction"]["trend"] == "declining"
    assert row["excluded_records"] == 2  # Next bimester plus the unclassified fixture evaluation.
    assert row["attendance_count"] == 0
