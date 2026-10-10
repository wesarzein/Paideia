"""Historical import and native evaluation coexist in isolated PostgreSQL."""
import os
from copy import deepcopy
from dataclasses import replace
from uuid import UUID

import pytest
from sqlalchemy import select
from test_grade_import_identity import client_for
from test_institutional_excel import preview, setup
from institutional_fixture import workbook_bytes
from test_roster_persistence import sessions as _sessions

from app.models.academic import CourseAssignment, GradeRecord
from app.models.student import Student
from app.models.user import Role, User
from app.services.evaluation_configuration import Competency, institutional_template, preview as calculate
from app.services.evaluation_revisions import create_revision

sessions = _sessions
pytestmark = pytest.mark.skipif(not os.environ.get("PAIDEIA_TEST_POSTGRES_URL"), reason="Isolated PostgreSQL required")


def test_historical_import_without_dates_and_native_teacher_evaluation(sessions):
    payload = setup(sessions)
    payload["academic_context"].update(historical=True, blocks={})
    with sessions() as db:
        teacher = User(role=Role(code="teacher", name="Docente"), email="history@test.invalid",
                       full_name="Docente sintético", password_hash="synthetic")
        db.add(teacher)
        db.flush()
        assignment = db.scalar(select(CourseAssignment).where(CourseAssignment.course_id == UUID(payload["course_id"])))
        assignment.teacher_id = teacher.id
        teacher_id = teacher.id
        configuration = institutional_template(payload["course_id"], payload["period_id"])
        configuration = replace(configuration, template_id="weighted_course_v1",
            competencies=(Competency("competency", "Competencia sintética", 0),),
            criteria=tuple(replace(item, name="Criterio nuevo " + item.key,
                competency_key="competency", weight=2, source_header=None) for item in configuration.criteria))
        revision = create_revision(db, configuration, teacher_id, "Configuración sintética", 0, "published")
        db.commit()
        revision_id = str(revision.id)
        pupil = db.scalar(select(Student))
        pupil_id = str(pupil.id)
    with client_for(sessions, "teacher", teacher_id) as client:
        payload["rows"] = preview(client, workbook_bytes("full"))["rows"]
        # Today's competencies differ from historical Excel criteria; history still loads.
        response = client.post("/imports/grades/commit", json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["imported"] == 160
        records = client.get("/grades").json()
        assert all(r["record_kind"] == "historical_bimester" and r["assessment_date"] is None
                   and r["evaluation_revision_id"] is None and r["component_id"] is None for r in records)
        assert client.post("/imports/grades/commit", json=payload).json()["skipped"] == 160
        native = dict(student_id=pupil_id, course_id=payload["course_id"], period_id=payload["period_id"],
            academic_bimester=2, evaluation_block=1, evaluation_criterion_key="b1_cuaderno",
            evaluation_name="Examen de hoy", evaluation_type="Criterio nuevo b1_cuaderno",
            assessment_date="2026-04-20", score=18)
        saved = client.post("/grades", json=native)
        assert saved.status_code == 201, saved.text
        assert saved.json()["record_kind"] == "evaluation"
        assert saved.json()["assessment_weight"] == 2
        assert saved.json()["evaluation_revision_id"] == revision_id
        assert client.post("/grades", json={**native, "assessment_date": None}).status_code == 422
        assert client.patch("/grades/" + records[0]["id"], json={"assessment_date": "2026-04-20"}).status_code == 422
        edited = deepcopy(payload)
        edited["rows"][0]["score"] = 5
        reviewed = client.post("/imports/grades/review", json=edited).json()
        edited["rows"][0].update(decision="update", review_token=reviewed["rows"][0]["review_token"])
        assert client.post("/imports/grades/commit", json=edited).json()["updated"] == 1
        assert len(client.get("/grades").json()) == 161
    with client_for(sessions, "teacher") as outsider:
        assert outsider.get("/grades").json() == []
        assert outsider.post("/imports/grades/commit", json=payload).status_code == 422
    with sessions() as db:
        from app.services.business_metrics import indicators
        metrics = indicators(db, db.get(User, teacher_id), {"course_id": UUID(payload["course_id"])})
        assert metrics["grade_count"] == 161
        assert metrics["weight_sum"] == 162


def test_weighted_calculation_uses_weights_and_omits_empty_optionals():
    from uuid import uuid4
    config = institutional_template(str(uuid4()), str(uuid4()))
    config = replace(config, template_id="weighted_course_v1", criteria=tuple(
        replace(c, weight=3 if c.key.endswith("cuaderno") else 1, is_optional=not c.key.endswith("cuaderno"))
        for c in config.criteria))
    result = calculate(config, {"b1_cuaderno": 10, "b2_cuaderno": 20})
    assert result["weighted_blocks"] == {"1": 10, "2": 20}
    assert result["formula_results"]["pf"] == 15
    assert result["warnings"] == []
