"""PostgreSQL-only checks prepared for the single disposable 4B.4 run."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from test_roster_persistence import roster
from test_roster_persistence import sessions as _sessions

from app.models.academic import (
    AcademicPeriod,
    Course,
    CourseAssessmentComponent,
    EvaluationConfigurationRevision,
    GradeRecord,
)
from app.models.student import Student
from app.models.user import Role, User
from app.services import school_roster
from app.services.evaluation_configuration import institutional_template
from app.services.evaluation_revisions import (
    StaleEvaluationRevision,
    create_revision,
)

sessions = _sessions
pytestmark = pytest.mark.skipif(
    not os.environ.get("PAIDEIA_TEST_POSTGRES_URL"),
    reason="Requires the named disposable PostgreSQL laboratory",
)


def seed(sessions):
    with sessions() as db:
        school_roster.synchronize_roster(db, roster())
        role = Role(code="phase4b4_teacher", name="Docente sintético 4B.4")
        user = User(
            role=role,
            email="phase4b4@synthetic.invalid",
            password_hash="synthetic",
            full_name="Docente Sintético 4B.4",
        )
        db.add_all([role, user])
        db.flush()
        course = db.scalar(select(Course))
        period = db.scalar(select(AcademicPeriod))
        student = db.scalar(select(Student))
        component = CourseAssessmentComponent(
            course_id=course.id, name="Cuaderno 4B.4", weight=2
        )
        db.add(component)
        db.commit()
        return user.id, course.id, period.id, student.id, component.id


def test_0014_upgrade_and_reversible_downgrade(sessions):
    with sessions() as db:
        inspector = inspect(db.bind)
        assert "evaluation_configuration_revisions" in inspector.get_table_names()
        assert "evaluation_revision_id" in {
            column["name"] for column in inspector.get_columns("grade_records")
        }

    command.downgrade(Config("alembic.ini"), "0013_grade_import_identity")
    with sessions() as db:
        inspector = inspect(db.bind)
        assert "evaluation_configuration_revisions" not in inspector.get_table_names()
        assert "evaluation_revision_id" not in {
            column["name"] for column in inspector.get_columns("grade_records")
        }
    command.upgrade(Config("alembic.ini"), "head")


def test_concurrent_first_revision_has_one_winner(sessions):
    actor_id, course_id, period_id, _student_id, _component_id = seed(sessions)
    configuration = institutional_template(str(course_id), str(period_id))
    barrier = Barrier(2)

    def publish():
        with sessions() as db:
            barrier.wait()
            try:
                revision = create_revision(
                    db, configuration, actor_id, "Publicación concurrente", 0, "published"
                )
                db.commit()
                return ("saved", revision.version)
            except (IntegrityError, StaleEvaluationRevision):
                db.rollback()
                return ("conflict", None)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: publish(), range(2)))
    assert sorted(result[0] for result in results) == ["conflict", "saved"]
    with sessions() as db:
        revisions = list(db.scalars(select(EvaluationConfigurationRevision)))
        assert len(revisions) == 1
        assert revisions[0].state == "published"


def test_database_preserves_grade_revision_and_append_only_history(sessions):
    actor_id, course_id, period_id, student_id, component_id = seed(sessions)
    configuration = institutional_template(str(course_id), str(period_id))
    with sessions() as db:
        revision = create_revision(
            db, configuration, actor_id, "Configuración publicada", 0, "published"
        )
        db.commit()
        grade = GradeRecord(
            student_id=student_id,
            course_id=course_id,
            period_id=period_id,
            component_id=component_id,
            evaluation_name="Semana 4",
            evaluation_type="Cuaderno",
            assessment_date=date(2026, 1, 28),
            score=14,
            evaluation_revision_id=revision.id,
        )
        db.add(grade)
        db.commit()
        assert grade.assessment_config["evaluation_revision_id"] == str(revision.id)
        assert grade.assessment_config["evaluation_revision_hash"] == revision.content_hash

        with pytest.raises(DBAPIError):
            db.execute(
                text("UPDATE evaluation_configuration_revisions SET reason='alterado' WHERE id=:id"),
                {"id": revision.id},
            )
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(
                text("UPDATE grade_records SET evaluation_revision_id=NULL WHERE id=:id"),
                {"id": grade.id},
            )
            db.commit()
        db.rollback()

        saved = db.get(GradeRecord, grade.id)
        assert saved.score == 14
        assert saved.evaluation_revision_id == revision.id
