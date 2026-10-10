from uuid import uuid4

import pytest
from test_academic_authorization import scenario, sessions

from app.endpoints.kpis import router
from app.models.academic import GradeRecord

__all__ = ["scenario", "sessions"]


def query(scenario, params=None):
    client = scenario[0]
    if not getattr(client.app.state, "kpis_added", False):
        client.app.include_router(router, prefix="/kpis")
        client.app.state.kpis_added = True
    return client.get("/kpis", params=params or {})


def test_teacher_aggregates_exclude_crossed_assignments(scenario):
    _, ids, actors, current = scenario
    current["user"] = actors["teacher"]
    result = query(scenario).json()
    assert result["grade_count"] == 2
    assert result["average"] == 11
    assert result["attendance"]["absent"] == 0
    assert result["coverage"]["active_enrollments"] == 2
    assert query(scenario, {"section_id": ids["sections"][2]}).json()["grade_count"] == 0
    assert (
        query(scenario, {"student_id": ids["students"][0], "course_id": ids["courses"][1]}).json()[
            "grade_count"
        ]
        == 0
    )


@pytest.mark.parametrize("role", ["student", "parent"])
def test_family_cannot_access_staff_analytics(scenario, role):
    _, _, actors, current = scenario
    current["user"] = actors[role]
    assert query(scenario).status_code == 403


def test_empty_evidence_is_not_zero(scenario):
    result = query(scenario, {"period_id": str(uuid4())}).json()
    assert result["average"] is None
    assert result["attendance"]["present_percent"] is None
    assert result["coverage"]["percent"] is None
    assert result["scope"] == "no_course_evidence"


def test_real_zero_and_template_boundaries(scenario, sessions):
    scenario[3]["user"] = scenario[2]["admin"]
    with sessions() as db:
        rows = db.query(GradeRecord).order_by(GradeRecord.id).all()
        for row, value in zip(rows, [0, 10.4, 13.4, 16.4, 20], strict=True):
            row.score = value
        db.commit()
    result = query(scenario).json()
    assert result["zero_scores"] == 1
    assert result["literal_distribution"] == {"AD": 1, "A": 1, "B": 1, "C": 2}
    assert result["average"] == pytest.approx(12.04)
    assert result["coverage"]["with_grades"] == 5
    assert sum(result["numeric_distribution"].values()) == 5
    assert result["evaluation_coverage"]["legacy_records_unknown"] == 5


def test_bimester_filter_does_not_invent_attendance_bimesters(scenario):
    scenario[3]["user"] = scenario[2]["admin"]
    _, ids, _, _ = scenario
    result = query(scenario, {"course_id": ids["courses"][0], "bimester": 2}).json()
    assert result["grade_count"] == 0
    assert result["attendance"]["count"] == 3
    assert result["attendance"]["scope"] == "full_period_not_bimester"
    assert result["coverage"]["without_grades"] == 3


def test_completion_uses_the_captured_revision_and_keeps_optional_policy_open(scenario, sessions):
    from app.services.evaluation_configuration import institutional_template
    from app.services.evaluation_revisions import create_revision

    _, ids, actors, current = scenario
    current["user"] = actors["admin"]
    with sessions() as db:
        from datetime import date
        from uuid import UUID

        configuration = institutional_template(ids["courses"][0], ids["period"])
        revision = create_revision(
            db, configuration, actors["admin"].id, "Synthetic", 0, "published"
        )
        db.flush()
        criterion = next(
            c for c in revision.configuration["criteria"] if c["is_active"] and c["block"] == 1
        )
        row = GradeRecord(
            student_id=UUID(ids["students"][0]),
            course_id=UUID(ids["courses"][0]),
            period_id=UUID(ids["period"]),
            evaluation_revision_id=revision.id,
            academic_bimester=1,
            evaluation_block=1,
            evaluation_criterion_key=criterion["key"],
            assessment_date=date(2026, 5, 1),
            score=0,
        )
        db.add(row)
        db.commit()
    result = query(scenario).json()
    assert result["evaluation_coverage"]["required_incomplete"] == 1
    assert result["evaluation_coverage"]["required_complete"] == 0
    assert result["evaluation_coverage"]["legacy_records_unknown"] == 5
