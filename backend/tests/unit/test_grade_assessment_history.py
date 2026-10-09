"""Historical calculation integrity using synthetic data and migrated PostgreSQL."""

import os
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from test_roster_persistence import roster
from test_roster_persistence import sessions as _sessions

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.endpoints import courses, grades
from app.models.academic import AcademicPeriod, Course, CourseAssessmentComponent, GradeRecord
from app.models.student import Student
from app.services import school_roster

sessions = _sessions

pytestmark = pytest.mark.skipif(
    not os.environ.get("PAIDEIA_TEST_POSTGRES_URL"), reason="Requires disposable PostgreSQL"
)


def seed(sessions):
    with sessions() as db:
        school_roster.synchronize_roster(db, roster())
        db.commit()
        student = db.scalar(select(Student))
        course = db.scalar(select(Course))
        period = db.scalar(select(AcademicPeriod))
        components = [
            CourseAssessmentComponent(course_id=course.id, name=f"Criterio {i}", weight=1)
            for i in range(5)
        ]
        db.add_all(components)
        db.commit()
        return {
            "student_id": str(student.id),
            "course_id": str(course.id),
            "period_id": str(period.id),
            "grade_id": str(student.grade_id),
            "section_id": str(student.section_id),
        }, [str(component.id) for component in components]


def api(sessions, role="admin"):
    app = FastAPI()
    app.include_router(grades.router, prefix="/grades")
    app.include_router(courses.router, prefix="/courses")

    def database():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(), role=SimpleNamespace(code=role)
    )
    return TestClient(app)


def add_grades(client, ids, components, month):
    records = []
    for component, score in zip(components, [10, 10, 10, 10, 20], strict=True):
        response = client.post(
            "/grades",
            json={
                **{k: ids[k] for k in ("student_id", "course_id", "period_id")},
                "component_id": component,
                "score": score,
                "assessment_date": f"2026-{month:02d}-01",
            },
        )
        assert response.status_code == 201, response.text
        records.append(response.json())
    return records


def average(client, ids, month):
    response = client.get(
        "/grades/monthly-summary",
        params={
            **{k: ids[k] for k in ("grade_id", "section_id", "course_id", "period_id")},
            "month": month,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["students"][0]["average"]


def test_original_defect_fixed_and_new_evaluations_use_new_weights(sessions):
    ids, components = seed(sessions)
    with api(sessions) as client:
        original = add_grades(client, ids, components, 4)
        assert average(client, ids, 4) == 12
        response = client.patch(
            f"/courses/{ids['course_id']}/assessment-components/{components[0]}",
            json={"weight": 3, "name": "Criterio renombrado", "is_optional": True},
        )
        assert response.status_code == 200
        # Explicitly reproduce the old query's defect on the same persisted rows.
        with sessions() as db:
            old_average = db.scalar(
                select(
                    func.sum(GradeRecord.score * CourseAssessmentComponent.weight)
                    / func.sum(CourseAssessmentComponent.weight)
                )
                .select_from(GradeRecord)
                .join(
                    CourseAssessmentComponent,
                    CourseAssessmentComponent.id == GradeRecord.component_id,
                )
            )
            assert round(old_average, 2) == 11.43
        assert average(client, ids, 4) == 12
        future = add_grades(client, ids, components, 5)
        assert future[0]["assessment_weight"] == 3
        assert average(client, ids, 5) == 11.43
        assert (
            client.delete(
                f"/courses/{ids['course_id']}/assessment-components/{components[0]}"
            ).status_code
            == 200
        )
        assert average(client, ids, 4) == 12
        persisted = {r["id"]: r for r in client.get("/grades").json()}
        for record in original:
            assert persisted[record["id"]] == record
    # A new API instance/connection observes the same persisted basis.
    with api(sessions) as restarted:
        assert average(restarted, ids, 4) == 12
        assert average(restarted, ids, 5) == 11.43


def test_grade_edits_and_component_reassignment_preserve_original_basis(sessions):
    ids, components = seed(sessions)
    with api(sessions) as client:
        original = add_grades(client, ids, components, 4)[0]
        client.patch(
            f"/courses/{ids['course_id']}/assessment-components/{components[1]}",
            json={"weight": 9},
        )
        response = client.patch(
            f"/grades/{original['id']}",
            json={
                "score": 15,
                "component_id": components[1],
                "qualitative_note": "Corrección explícita",
                "assessment_weight": 9,
                "assessment_config": {"weight": 9},
            },
        )
        assert response.status_code == 200, response.text
        edited = response.json()
        assert edited["score"] == 15
        assert edited["component_id"] == components[1]
        assert edited["assessment_weight"] == 1
        assert edited["assessment_config"] == original["assessment_config"]
        assert average(client, ids, 4) == 13


def test_database_blocks_snapshot_rewrites_and_rolls_back(sessions):
    ids, components = seed(sessions)
    with api(sessions) as client:
        original = add_grades(client, ids, components, 4)[0]
    for assignment in ("assessment_weight = 9", "assessment_config = '{}'::json"):
        with sessions() as db:
            with pytest.raises(DBAPIError, match="immutable"):
                db.execute(
                    text(f"UPDATE grade_records SET {assignment} WHERE id = :id"),
                    {"id": original["id"]},
                )
                db.commit()
            db.rollback()
            record = db.get(GradeRecord, original["id"])
            assert record.assessment_weight == 1
            assert record.assessment_config == original["assessment_config"]


def test_orm_rejects_configuration_rewrites_without_saving_other_changes(sessions):
    ids, components = seed(sessions)
    with api(sessions) as client:
        original = add_grades(client, ids, components, 4)[0]
    with sessions() as db:
        record = db.get(GradeRecord, original["id"])
        record.score = 5
        record.assessment_weight = 9
        with pytest.raises(ValueError, match="inmutable"):
            db.commit()
        db.rollback()
        assert record.score == 10
        assert record.assessment_weight == 1


def test_zero_weight_and_unlinked_grades_and_raw_inserts(sessions):
    ids, components = seed(sessions)
    with sessions() as db:
        db.get(CourseAssessmentComponent, components[0]).weight = 0
        db.commit()
        for component, expected in ((components[0], 0), (None, 1)):
            record_id = uuid4()
            db.execute(
                GradeRecord.__table__.insert().values(
                    id=record_id,
                    student_id=ids["student_id"],
                    course_id=ids["course_id"],
                    period_id=ids["period_id"],
                    component_id=component,
                    score=0,
                    assessment_date=date(2026, 4, 1),
                )
            )
            db.commit()
            record = db.get(GradeRecord, record_id)
            assert record.score == 0
            assert record.assessment_weight == expected
            assert record.assessment_config["weight"] == expected


def test_roles_unchanged(sessions):
    ids, components = seed(sessions)
    with api(sessions, "teacher") as client:
        assert (
            client.patch(
                f"/courses/{ids['course_id']}/assessment-components/{components[0]}",
                json={"weight": 3},
            ).status_code
            == 403
        )
    with api(sessions, "coordinator") as client:
        assert (
            client.post(
                "/grades",
                json={
                    **{k: ids[k] for k in ("student_id", "course_id", "period_id")},
                    "score": 10,
                },
            ).status_code
            == 403
        )


@pytest.mark.parametrize("sessions", ["0011_evidence_types"], indirect=True)
def test_migration_preserves_legacy_values_ids_and_links(sessions):
    ids, components = seed(sessions)
    with sessions() as db:
        db.get(CourseAssessmentComponent, components[0]).weight = 3
        db.get(CourseAssessmentComponent, components[1]).weight = 0
        db.commit()
        for component, score in zip(
            (components[0], components[1], None), (10, 20, 15), strict=True
        ):
            db.execute(
                GradeRecord.__table__.insert().values(
                    id=uuid4(),
                    student_id=ids["student_id"],
                    course_id=ids["course_id"],
                    period_id=ids["period_id"],
                    component_id=component,
                    score=score,
                    assessment_date=date(2026, 4, 1),
                )
            )
        db.commit()
        columns = (
            "id, student_id, course_id, period_id, component_id, score, created_at, updated_at"
        )
        before = db.execute(text(f"SELECT {columns} FROM grade_records ORDER BY id")).all()
    command.upgrade(Config("alembic.ini"), "head")
    with sessions() as db:
        assert db.execute(text(f"SELECT {columns} FROM grade_records ORDER BY id")).all() == before
        records = db.scalars(select(GradeRecord)).all()
        assert sorted(record.assessment_weight for record in records) == [0, 1, 3]
        assert all(record.assessment_config["origin"] == "legacy_migration" for record in records)
        db.get(CourseAssessmentComponent, components[0]).weight = 9
        db.commit()
    command.upgrade(Config("alembic.ini"), "head")
    with api(sessions) as client:
        assert average(client, ids, 4) == 11.25
