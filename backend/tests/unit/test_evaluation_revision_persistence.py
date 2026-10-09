from dataclasses import replace
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.database import Base
from app.core.database import get_db
from app.endpoints.courses import router as courses_router
from app.models import base as _mapped_models  # noqa: F401 - register all foreign-key tables
from app.models.academic import (
    AcademicPeriod,
    Course,
    CourseAssessmentComponent,
    CourseAssignment,
    EvaluationConfigurationRevision,
    Grade,
    GradeRecord,
    Section,
)
from app.models.student import Student
from app.models.user import Role, User
from app.services.evaluation_configuration import institutional_template
from app.services.evaluation_revisions import (
    StaleEvaluationRevision,
    create_revision,
    latest_published_revision,
    latest_revision,
    revision_configuration,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        role = Role(code="teacher", name="Docente")
        user = User(
            role=role,
            email="teacher@example.test",
            password_hash="synthetic",
            full_name="Docente Sintético",
        )
        course = Course(name="Curso sintético", code="SYN-4B4")
        period = AcademicPeriod(
            name="Periodo sintético", starts_on=date(2026, 1, 1), ends_on=date(2026, 2, 28)
        )
        student = Student(student_code="SYN001", first_name="Ada", last_name="Prueba")
        component = CourseAssessmentComponent(
            course_id=course.id, name="Cuaderno", weight=1, is_optional=False
        )
        session.add_all([role, user, course, period, student])
        session.flush()
        component.course_id = course.id
        session.add(component)
        session.commit()
        yield session, user, course, period, student, component


def test_revision_history_is_append_only_and_rejects_stale_edits(db):
    session, user, course, period, _student, _component = db
    configuration = institutional_template(str(course.id), str(period.id))

    draft = create_revision(session, configuration, user.id, "Borrador inicial", 0, "draft")
    session.commit()
    published = create_revision(
        session, configuration, user.id, "Publicación revisada", 1, "published"
    )
    session.commit()

    assert published.version == 2
    assert published.previous_revision_id == draft.id
    assert latest_revision(session, course.id, period.id).id == published.id
    assert latest_published_revision(session, course.id, period.id).id == published.id
    assert revision_configuration(draft).fingerprint() == configuration.fingerprint()

    with pytest.raises(StaleEvaluationRevision):
        create_revision(session, configuration, user.id, "Edición obsoleta", 1, "draft")

    published.reason = "Intento de sobrescritura"
    with pytest.raises(ValueError, match="inmutables"):
        session.commit()
    session.rollback()


def test_new_grade_keeps_the_published_revision_snapshot(db):
    session, user, course, period, student, component = db
    configuration = institutional_template(str(course.id), str(period.id))
    published = create_revision(
        session, configuration, user.id, "Configuración vigente", 0, "published"
    )
    session.commit()

    grade = GradeRecord(
        student_id=student.id,
        course_id=course.id,
        period_id=period.id,
        component_id=component.id,
        evaluation_name="Semana 4",
        evaluation_type="Cuaderno",
        assessment_date=date(2026, 1, 28),
        score=12,
        evaluation_revision_id=published.id,
    )
    session.add(grade)
    session.commit()
    original_snapshot = dict(grade.assessment_config)

    changed_criteria = tuple(
        replace(criterion, weight=4)
        if criterion.key == "b1_cuaderno"
        else criterion
        for criterion in configuration.criteria
    )
    changed = replace(configuration, criteria=changed_criteria, template_id="custom_v1")
    newer = create_revision(
        session, changed, user.id, "Nueva ponderación", 1, "published"
    )
    session.commit()
    session.refresh(grade)

    assert newer.version == 2
    assert grade.evaluation_revision_id == published.id
    assert grade.assessment_config == original_snapshot
    assert grade.assessment_config["evaluation_revision_version"] == 1
    assert grade.assessment_config["evaluation_revision_hash"] == configuration.fingerprint()


def test_grade_rejects_draft_or_wrong_scope_revision(db):
    session, user, course, period, student, component = db
    configuration = institutional_template(str(course.id), str(period.id))
    draft = create_revision(session, configuration, user.id, "Aún no publicado", 0, "draft")
    session.commit()
    grade = GradeRecord(
        student_id=student.id,
        course_id=course.id,
        period_id=period.id,
        component_id=component.id,
        evaluation_name="Semana 4",
        evaluation_type="Cuaderno",
        assessment_date=date(2026, 1, 28),
        score=12,
        evaluation_revision_id=draft.id,
    )
    session.add(grade)
    with pytest.raises(ValueError, match="no está publicada"):
        session.commit()
    session.rollback()
    assert session.scalar(select(GradeRecord.id)) is None


def test_scope_and_content_hash_are_checked_when_loading(db):
    session, user, course, period, _student, _component = db
    configuration = institutional_template(str(course.id), str(period.id))
    revision = create_revision(
        session, configuration, user.id, "Configuración válida", 0, "published"
    )
    session.commit()

    revision.configuration = {**revision.configuration, "template_id": "custom_v1"}
    with pytest.raises(ValueError, match="inmutables"):
        session.commit()
    session.rollback()

    stored = session.get(EvaluationConfigurationRevision, revision.id)
    stored.content_hash = "0" * 64
    with pytest.raises(ValueError, match="inmutables"):
        session.commit()


def test_http_permissions_publication_history_and_restore(db):
    session, teacher, course, period, _student, _component = db
    application = FastAPI()
    application.include_router(courses_router, prefix="/courses")

    def session_override():
        yield session

    current_user = {"value": teacher}

    def user_override():
        return current_user["value"]

    application.dependency_overrides[get_db] = session_override
    application.dependency_overrides[get_current_user] = user_override
    client = TestClient(application)
    configuration = institutional_template(str(course.id), str(period.id)).document()
    payload = {"configuration": configuration, "expected_version": 0, "reason": "Borrador"}

    denied = client.post(f"/courses/{course.id}/evaluation-configurations/drafts", json=payload)
    assert denied.status_code == 403

    grade = Grade(name="1°", level="Secundaria")
    session.add(grade)
    session.flush()
    section = Section(grade_id=grade.id, name="A")
    session.add(section)
    session.flush()
    session.add(
        CourseAssignment(
            course_id=course.id,
            grade_id=grade.id,
            section_id=section.id,
            teacher_id=teacher.id,
            teacher_name=teacher.full_name,
        )
    )
    session.commit()

    saved = client.post(f"/courses/{course.id}/evaluation-configurations/drafts", json=payload)
    assert saved.status_code == 201
    assert saved.json()["state"] == "draft"
    assert saved.json()["version"] == 1

    stale = client.post(f"/courses/{course.id}/evaluation-configurations/drafts", json=payload)
    assert stale.status_code == 409

    payload.update(expected_version=1, reason="Publicación explícita")
    published = client.post(
        f"/courses/{course.id}/evaluation-configurations/publish", json=payload
    )
    assert published.status_code == 201
    assert published.json()["state"] == "published"

    versions = client.get(
        f"/courses/{course.id}/evaluation-configurations/versions",
        params={"period_id": str(period.id)},
    )
    assert [item["version"] for item in versions.json()] == [2, 1]

    director_role = Role(code="director", name="Director")
    director = User(
        role=director_role,
        email="director@example.test",
        password_hash="synthetic",
        full_name="Director Sintético",
    )
    session.add_all([director_role, director])
    session.commit()
    current_user["value"] = director
    forbidden = client.post(
        f"/courses/{course.id}/evaluation-configurations/publish",
        json={**payload, "expected_version": 2},
    )
    assert forbidden.status_code == 403

    current_user["value"] = teacher
    restored = client.post(
        f"/courses/{course.id}/evaluation-configurations/restore-institutional",
        json={
            "period_id": str(period.id),
            "expected_version": 2,
            "reason": "Restablecimiento explícito",
        },
    )
    assert restored.status_code == 201
    assert restored.json()["version"] == 3
    assert restored.json()["configuration"]["template_id"] == "institutional_v1"
