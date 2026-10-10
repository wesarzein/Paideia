"""Integration tests restricted to disposable PostgreSQL and synthetic grades."""

import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from test_roster_persistence import roster
from test_roster_persistence import sessions as _sessions

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.endpoints import grades, imports
from app.models.academic import (
    AcademicPeriod,
    Course,
    CourseAssessmentComponent,
    CourseAssignment,
    GradeRecord,
    GradeRecordIdentity,
)
from app.models.student import Student
from app.models.user import AuditLog, Role, User
from app.services import grade_import_identity, school_roster

sessions = _sessions
pytestmark = pytest.mark.skipif(
    not os.environ.get("PAIDEIA_TEST_POSTGRES_URL"), reason="Requires disposable PostgreSQL"
)


def context(sessions):
    with sessions() as db:
        school_roster.synchronize_roster(db, roster())
        db.commit()
        student = db.scalar(select(Student))
        return {
            "course_id": str(db.scalar(select(Course)).id),
            "period_id": str(db.scalar(select(AcademicPeriod)).id),
            "rows": [
                {
                    "student_code": student.student_code,
                    "score": i,
                    "evaluation_name": f"Evaluación sintética {i}",
                    "evaluation_type": "Cuaderno",
                    "assessment_date": "2026-04-01",
                }
                for i in range(10)
            ],
        }


def client_for(sessions, role="admin", user_id=None):
    app = FastAPI()
    app.include_router(imports.router, prefix="/imports")
    app.include_router(grades.router, prefix="/grades")
    user = SimpleNamespace(id=user_id or uuid4(), role=SimpleNamespace(code=role))

    def database():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_ten_rows_reimport_without_duplicates(sessions):
    payload = context(sessions)
    with client_for(sessions) as client:
        first = client.post("/imports/grades/commit", json=payload)
        assert first.status_code == 200, first.text
        assert first.json()["imported"] == 10
        before = client.get("/grades").json()
        second = client.post("/imports/grades/commit", json=payload)
        assert second.status_code == 200, second.text
        with sessions() as db:
            assert db.scalar(select(func.count()).select_from(GradeRecord)) == 10
        assert second.json()["imported"] == 0
        assert client.get("/grades").json() == before


def test_mixed_new_and_existing_and_duplicates_within_file(sessions):
    payload = context(sessions)
    with client_for(sessions) as client:
        assert client.post("/imports/grades/commit", json=payload).status_code == 200
        mixed = deepcopy(payload)
        mixed["rows"].extend(
            [
                dict(payload["rows"][0], evaluation_name="Nueva evaluación"),
                dict(payload["rows"][0], evaluation_name="Nueva evaluación"),
            ]
        )
        result = client.post("/imports/grades/commit", json=mixed)
        assert result.status_code == 200, result.text
        assert result.json() == {
            "processed": 12,
            "imported": 1,
            "updated": 0,
            "skipped": 11,
            "rejected": 0,
        }
        conflicting = deepcopy(mixed)
        conflicting["rows"][-1]["score"] = 19
        assert client.post("/imports/grades/commit", json=conflicting).status_code == 422
        assert len(client.get("/grades").json()) == 11


def test_nullable_legacy_timestamp_does_not_break_review_or_update(sessions):
    payload = context(sessions)
    payload["rows"] = payload["rows"][:1]
    with client_for(sessions) as client:
        assert client.post("/imports/grades/commit", json=payload).status_code == 200
        original = client.get("/grades").json()[0]
        with sessions() as db:
            db.execute(GradeRecord.__table__.update().values(updated_at=None))
            db.commit()
        response = client.post("/imports/grades/review", json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["rows"][0]["status"] == "identical"
        payload["rows"][0]["score"] = 12
        review = client.post("/imports/grades/review", json=payload).json()["rows"][0]
        payload["rows"][0].update(decision="update", review_token=review["review_token"])
        assert client.post("/imports/grades/commit", json=payload).status_code == 200
        saved = client.get("/grades").json()[0]
        assert saved["score"] == 12
        assert saved["assessment_config"] == original["assessment_config"]


def test_teacher_corrections_require_review_and_explicit_update(sessions):
    payload = context(sessions)
    with client_for(sessions) as client:
        client.post("/imports/grades/commit", json=payload)
        record = next(r for r in client.get("/grades").json() if r["score"] == 0)
        assert client.patch(f"/grades/{record['id']}", json={"score": 17}).status_code == 200
        assert client.post("/imports/grades/commit", json=payload).status_code == 409
        review = client.post("/imports/grades/review", json=payload)
        assert review.status_code == 200
        item = review.json()["rows"][0]
        assert item["status"] == "different"
        assert item["existing"]["score"] == 17
        preserve = deepcopy(payload)
        preserve["rows"][0]["decision"] = "keep"
        assert client.post("/imports/grades/commit", json=preserve).json()["skipped"] == 10
        assert (
            next(r for r in client.get("/grades").json() if r["id"] == record["id"])["score"] == 17
        )
        update = deepcopy(payload)
        update["rows"][0].update(decision="update", review_token=item["review_token"])
        result = client.post("/imports/grades/commit", json=update)
        assert result.status_code == 200, result.text
        assert result.json()["updated"] == 1
        after = next(r for r in client.get("/grades").json() if r["id"] == record["id"])
        assert after["score"] == 0
        assert after["assessment_config"] == record["assessment_config"]
        assert after["assessment_weight"] == record["assessment_weight"]
        with sessions() as db:
            assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


@pytest.mark.parametrize("change", ["existing", "incoming", "token", "actor"])
def test_stale_modified_or_forged_confirmation_rejected(sessions, change):
    payload = context(sessions)
    payload["rows"] = payload["rows"][:1]
    with client_for(sessions) as client:
        client.post("/imports/grades/commit", json=payload)
        record = client.get("/grades").json()[0]
        client.patch(f"/grades/{record['id']}", json={"score": 17})
        token = client.post("/imports/grades/review", json=payload).json()["rows"][0][
            "review_token"
        ]
        payload["rows"][0].update(decision="update", review_token=token)
        if change == "existing":
            client.patch(f"/grades/{record['id']}", json={"score": 19})
        elif change == "incoming":
            payload["rows"][0]["score"] = 5
        elif change == "token":
            payload["rows"][0]["review_token"] = "forged"
        if change == "actor":
            with client_for(sessions) as other:
                response = other.post("/imports/grades/commit", json=payload)
        else:
            response = client.post("/imports/grades/commit", json=payload)
        assert response.status_code == 409
        assert client.get("/grades").json()[0]["score"] == (19 if change == "existing" else 17)


def test_manual_grades_match_and_distinct_dimensions_remain_distinct(sessions):
    payload = context(sessions)
    payload["rows"] = payload["rows"][:1]
    with sessions() as db:
        student = db.scalar(select(Student))
        component = CourseAssessmentComponent(
            course_id=payload["course_id"], name="Cuaderno", weight=3
        )
        db.add(component)
        db.commit()
        component_id, student_id = str(component.id), str(student.id)
    row = payload["rows"][0]
    manual = dict(
        student_id=student_id,
        course_id=payload["course_id"],
        period_id=payload["period_id"],
        component_id=component_id,
        score=row["score"],
        evaluation_name=row["evaluation_name"],
        evaluation_type=row["evaluation_type"],
        assessment_date=row["assessment_date"],
    )
    with client_for(sessions) as client:
        first = client.post("/grades", json=manual)
        assert first.status_code == 201, first.text
        assert (
            client.post("/imports/grades/review", json=payload).json()["rows"][0]["component_id"]
            == component_id
        )
        assert client.post("/imports/grades/commit", json=payload).json()["imported"] == 0
        assert client.post("/grades", json=manual).status_code == 409
        for variant in (
            {"evaluation_name": "Otra evaluación"},
            {"assessment_date": "2026-04-02"},
            {"evaluation_type": "Evaluación"},
            {"component_id": None},
        ):
            assert client.post("/grades", json={**manual, **variant}).status_code == 201
        assert len(client.get("/grades").json()) == 5
        ambiguous = client.post("/imports/grades/review", json=payload)
        assert ambiguous.json()["rows"][0]["status"] == "ambiguous"
        payload["rows"][0]["component_id"] = component_id
        assert client.post("/imports/grades/commit", json=payload).json()["skipped"] == 1


def test_import_rollback_for_invalid_and_conflicting_rows(sessions):
    payload = context(sessions)
    with client_for(sessions) as client:
        bad = deepcopy(payload)
        bad["rows"][-1]["score"] = 21
        assert client.post("/imports/grades/commit", json=bad).status_code == 422
        assert client.get("/grades").json() == []
        client.post("/imports/grades/commit", json={**payload, "rows": payload["rows"][:1]})
        changed = deepcopy(payload)
        changed["rows"][0]["score"] = 19
        assert client.post("/imports/grades/commit", json=changed).status_code == 409
        assert len(client.get("/grades").json()) == 1
        assert client.get("/grades").json()[0]["score"] == 0


def test_concurrent_confirmations_import_once(sessions):
    payload = context(sessions)
    barrier = Barrier(2)

    def confirm():
        with client_for(sessions) as client:
            barrier.wait(timeout=15)
            result = client.post("/imports/grades/commit", json=payload)
            assert result.status_code == 200, result.text
            return result.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: confirm(), range(2)))
    assert sorted(result["imported"] for result in results) == [0, 10]
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(GradeRecord)) == 10


def test_database_uniqueness_and_rollback_for_direct_writers(sessions):
    payload = context(sessions)
    with client_for(sessions) as client:
        client.post("/imports/grades/commit", json={**payload, "rows": payload["rows"][:1]})
        original = client.get("/grades").json()[0]
    with sessions() as db:
        record = db.get(GradeRecord, original["id"])
        record.score = 15
        db.flush()
        with pytest.raises(IntegrityError):
            db.execute(
                GradeRecord.__table__.insert().values(
                    id=uuid4(),
                    student_id=record.student_id,
                    course_id=record.course_id,
                    period_id=record.period_id,
                    component_id=record.component_id,
                    evaluation_name=record.evaluation_name,
                    evaluation_type=record.evaluation_type,
                    assessment_date=record.assessment_date,
                    score=19,
                )
            )
        db.rollback()
        assert record.score == 0
        assert record.assessment_config == original["assessment_config"]


def test_concurrent_different_updates_require_fresh_review(sessions):
    payload = context(sessions)
    payload["rows"] = payload["rows"][:1]
    actor = uuid4()
    proposals = []
    with client_for(sessions, user_id=actor) as client:
        client.post("/imports/grades/commit", json=payload)
        for score in (12, 18):
            proposal = deepcopy(payload)
            proposal["rows"][0]["score"] = score
            token = client.post("/imports/grades/review", json=proposal).json()["rows"][0][
                "review_token"
            ]
            proposal["rows"][0].update(decision="update", review_token=token)
            proposals.append(proposal)
    barrier = Barrier(2)

    def update(proposal):
        with client_for(sessions, user_id=actor) as client:
            barrier.wait(timeout=15)
            return client.post("/imports/grades/commit", json=proposal).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(update, proposals)) == [200, 409]
    with sessions() as db:
        assert db.scalar(select(GradeRecord)).score in (12, 18)
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


def test_import_database_conflict_rolls_back_entire_batch(sessions, monkeypatch):
    payload = context(sessions)
    original_inspect = grade_import_identity.inspect_rows

    def concurrent_manual_writer(db, user, incoming, raw_rows, *, lock=False):
        result = original_inspect(db, user, incoming, raw_rows, lock=lock)
        # A manual insert wins after the import has checked for existing rows.
        last = incoming[-1]
        with sessions() as rival:
            rival.add(
                GradeRecord(
                    student_id=last.student_id,
                    course_id=last.course_id,
                    period_id=last.period_id,
                    component_id=last.component_id,
                    evaluation_name=last.evaluation_name,
                    evaluation_type=last.evaluation_type,
                    assessment_date=last.assessment_date,
                    score=18,
                )
            )
            rival.commit()
        return result

    monkeypatch.setattr(grade_import_identity, "inspect_rows", concurrent_manual_writer)
    with client_for(sessions) as client:
        assert client.post("/imports/grades/commit", json=payload).status_code == 409
        records = client.get("/grades").json()
        assert len(records) == 1
        assert records[0]["score"] == 18
        assert records[0]["evaluation_name"] == payload["rows"][-1]["evaluation_name"]


def test_teacher_assignments_and_role_checks(sessions):
    payload = context(sessions)
    with sessions() as db:
        role = Role(code="teacher", name="Docente sintético")
        db.add(role)
        db.flush()
        user = User(
            role_id=role.id,
            email="teacher@synthetic.invalid",
            full_name="Docente sintético",
            password_hash="not-a-login-password",
        )
        db.add(user)
        db.flush()
        db.scalar(select(CourseAssignment)).teacher_id = user.id
        db.commit()
        teacher_id = user.id
    with client_for(sessions, "teacher", teacher_id) as teacher:
        assert teacher.post("/imports/grades/review", json=payload).status_code == 200
        assert teacher.post("/imports/grades/commit", json=payload).status_code == 200
        payload["rows"][0]["score"] = 18
        review = teacher.post("/imports/grades/review", json=payload).json()["rows"][0]
        payload["rows"][0].update(decision="update", review_token=review["review_token"])
        confirmed = teacher.post("/imports/grades/commit", json=payload)
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["updated"] == 1
    with client_for(sessions, "teacher") as other:
        assert other.post("/imports/grades/review", json=payload).status_code == 422
        assert other.post("/imports/grades/commit", json=payload).status_code == 422
    with client_for(sessions, "student") as student:
        assert student.post("/imports/grades/review", json=payload).status_code == 403
        assert student.post("/imports/grades/commit", json=payload).status_code == 403


@pytest.mark.parametrize("sessions", ["0012_grade_assessment_snapshot"], indirect=True)
def test_migration_preserves_and_reserves_historical_duplicate_groups(sessions):
    payload = context(sessions)
    with sessions() as db:
        student = db.scalar(select(Student))
        for score in (0, 18):
            db.execute(
                GradeRecord.__table__.insert().values(
                    id=uuid4(),
                    student_id=student.id,
                    course_id=payload["course_id"],
                    period_id=payload["period_id"],
                    score=score,
                    evaluation_name=payload["rows"][0]["evaluation_name"],
                    evaluation_type="Cuaderno",
                    assessment_date="2026-04-01",
                )
            )
        db.commit()
        # The pre-0014 schema has no configurable-context columns yet.
        before = db.execute(text("SELECT * FROM grade_records ORDER BY id")).mappings().all()
    command.upgrade(Config("alembic.ini"), "head")
    with sessions() as db:
        after = db.execute(text("SELECT * FROM grade_records ORDER BY id")).mappings().all()
        assert [{key: row[key] for key in before[0]} for row in after] == before
        assert db.scalar(select(GradeRecordIdentity)).grade_id is None
    with client_for(sessions) as client:
        assert (
            client.post("/imports/grades/review", json=payload).json()["rows"][0]["status"]
            == "ambiguous"
        )
        assert client.post("/imports/grades/commit", json=payload).status_code == 422
        assert len(client.get("/grades").json()) == 2
