"""Synthetic records in SQLite or an explicitly named disposable PostgreSQL."""

import hashlib
import json
import os
from datetime import date
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import (
    AcademicPeriod,
    AttendanceRecord,
    Base,
    Course,
    CourseAssignment,
    Enrollment,
    FollowUp,
    Grade,
    GradeRecord,
    Section,
    Student,
)
from app.services import school_roster


@pytest.fixture
def sessions(monkeypatch, request):
    postgres_url = os.environ.get("PAIDEIA_TEST_POSTGRES_URL")
    if postgres_url:
        url = make_url(postgres_url)
        # Never allow this opt-in fixture to target an institutional database.
        if (
            url.drivername != "postgresql+psycopg"
            or url.host != "paideia-phase2-testdb"
            or url.database != "paideia_phase2_test"
            or url.username != "phase2_test"
        ):
            pytest.fail("PostgreSQL tests require the dedicated phase2 container/database")
        schema = f"phase2_{uuid4().hex}"
        provisioner = create_engine(url)
        with provisioner.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        provisioner.dispose()
        url = url.update_query_dict({"options": f"-csearch_path={schema}"})
        from app.core.config import settings

        monkeypatch.setattr(settings, "database_url", url.render_as_string(hide_password=False))
        command.upgrade(Config("alembic.ini"), getattr(request, "param", "head"))
        engine = create_engine(url)
        yield sessionmaker(bind=engine, autoflush=False)
        engine.dispose()
        # Keep synthetic schemas for inspection; never issue DROP/DELETE cleanup.
        return
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def enforce_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


def roster(students=None, courses=None):
    return {
        "school_year": 2026,
        "sections": [
            {
                "level": "Secundaria",
                "grade": "1°",
                "section": "A",
                "students": students if students is not None else ["Ejemplo, Uno"],
                "courses": courses if courses is not None else [{"name": "Matemática"}],
            }
        ],
    }


def seed_history(sessions):
    with sessions() as db:
        school_roster.synchronize_roster(db, roster())
        student = db.scalar(select(Student))
        course = db.scalar(select(Course))
        period = db.scalar(select(AcademicPeriod))
        # This code used to trigger deletion of the student and all its histories.
        student.student_code = "STU-1001"
        records = [
            GradeRecord(
                student_id=student.id,
                course_id=course.id,
                period_id=period.id,
                score=17,
                assessment_date=date(2026, 10, 1),
            ),
            AttendanceRecord(
                student_id=student.id,
                course_id=course.id,
                period_id=period.id,
                status="PRESENT",
                attendance_date=date(2026, 10, 1),
            ),
            FollowUp(student_id=student.id, action="Seguimiento sintético"),
        ]
        db.add_all(records)
        db.commit()
        return student.id, [record.id for record in records]


def assert_history(db, student_id, record_ids):
    for model, record_id in zip((GradeRecord, AttendanceRecord, FollowUp), record_ids, strict=True):
        assert db.get(model, record_id).student_id == student_id
    assert db.get(GradeRecord, record_ids[0]).score == 17
    assert db.get(FollowUp, record_ids[2]).action == "Seguimiento sintético"


def test_startup_never_reads_or_synchronizes_roster(sessions, monkeypatch):
    from app import main

    student_id, record_ids = seed_history(sessions)

    def forbidden(*_args, **_kwargs):
        pytest.fail("Startup must never access the roster")

    monkeypatch.setattr(main, "SessionLocal", sessions)
    monkeypatch.setattr(main.settings, "initial_admin_email", None)
    monkeypatch.setattr(main.settings, "initial_admin_password", None)
    monkeypatch.setattr(school_roster, "load_roster", forbidden)
    monkeypatch.setattr(school_roster, "synchronize_roster", forbidden)
    # Also catch a future direct import into main.
    monkeypatch.setattr(main, "load_roster", forbidden, raising=False)
    monkeypatch.setattr(main, "synchronize_roster", forbidden, raising=False)
    for _restart in range(2):
        with TestClient(main.create_app()) as client:
            assert client.get("/api/v1/health").status_code == 200
    with sessions() as db:
        assert db.get(Student, student_id).student_code == "STU-1001"
        assert db.get(Student, student_id).status == "ACTIVE"
        assert_history(db, student_id, record_ids)


def test_partial_roster_preserves_absent_records_and_configuration(sessions):
    student_id, record_ids = seed_history(sessions)
    with sessions() as db:
        student = db.get(Student, student_id)
        course = db.scalar(select(Course))
        assignment = db.scalar(select(CourseAssignment))
        assignment.teacher_name = "Docente sintético manual"
        period = db.scalar(select(AcademicPeriod))
        period.starts_on = date(2026, 3, 10)
        other_grade = Grade(name="2°", level="Secundaria", is_active=True)
        db.add(other_grade)
        db.flush()
        other_section = Section(name="B", grade_id=other_grade.id, is_active=True)
        db.add(other_section)
        db.commit()
        assignment_id, course_id = assignment.id, course.id
        other_ids = other_grade.id, other_section.id
        # Existing student/course omitted; creates unrelated entries only.
        school_roster.synchronize_roster(db, roster(["Nuevo, Dos"], [{"name": "Historia"}]))
        db.commit()
        assert student.status == "ACTIVE"
        assert db.get(Course, course_id).is_active
        assert db.get(CourseAssignment, assignment_id).teacher_name == "Docente sintético manual"
        assert db.get(Grade, other_ids[0]).is_active
        assert db.get(Section, other_ids[1]).is_active
        assert period.starts_on == date(2026, 3, 10)
        assert (
            db.scalar(select(Enrollment).where(Enrollment.student_id == student_id)).status
            == "ACTIVE"
        )
        assert_history(db, student_id, record_ids)


def test_reorder_and_insert_preserve_codes_and_ids(sessions):
    with sessions() as db:
        school_roster.synchronize_roster(db, roster(["Ejemplo, Uno", "Ejemplo, Dos"]))
        db.commit()
        original = {s.first_name: (s.id, s.student_code) for s in db.scalars(select(Student))}
        school_roster.synchronize_roster(
            db, roster(["Ejemplo, Tres", "Ejemplo, Dos", "Ejemplo, Uno"])
        )
        db.commit()
        after = {s.first_name: (s.id, s.student_code) for s in db.scalars(select(Student))}
        assert after["Uno"] == original["Uno"]
        assert after["Dos"] == original["Dos"]
        assert after["Tres"][1] == "1SA003"
        assert not any(
            school_roster.synchronize_roster(
                db, roster(["Ejemplo, Dos", "Ejemplo, Uno", "Ejemplo, Tres"])
            ).values()
        )


def test_explicit_update_keeps_identity_and_all_history(sessions):
    student_id, record_ids = seed_history(sessions)
    changed = roster(
        [
            {
                "id": str(student_id),
                "student_code": "STU-1001",
                "last_name": "Corregido",
                "first_name": "Uno",
            }
        ]
    )
    changed["sections"][0]["grade"] = "2°"
    with sessions() as db:
        school_roster.synchronize_roster(db, changed, update_existing=True)
        db.commit()
        student = db.get(Student, student_id)
        assert student.last_name == "Corregido"
        assert student.student_code == "STU-1001"
        assert db.get(Grade, student.grade_id).name == "2°"
        assert_history(db, student_id, record_ids)


def test_existing_inactive_records_are_not_reactivated_or_overwritten(sessions):
    student_id, _ = seed_history(sessions)
    with sessions() as db:
        db.get(Student, student_id).status = "INACTIVE"
        course = db.scalar(select(Course))
        course.is_active = False
        course.code = "MANUAL-CODE"
        enrollment = db.scalar(select(Enrollment))
        enrollment.status = "INACTIVE"
        assignment = db.scalar(select(CourseAssignment))
        assignment.teacher_name = "Docente manual"
        db.commit()
        school_roster.synchronize_roster(
            db, roster(courses=[{"name": "Matemática", "teacher": "Etiqueta del archivo"}])
        )
        db.commit()
        assert db.get(Student, student_id).status == "INACTIVE"
        assert not course.is_active
        assert course.code == "MANUAL-CODE"
        assert enrollment.status == "INACTIVE"
        assert assignment.teacher_name == "Docente manual"


def test_changes_require_opt_in_and_stable_identity(sessions):
    student_id, _ = seed_history(sessions)
    with sessions() as db:
        changed = roster([{"id": str(student_id), "last_name": "Corregido", "first_name": "Uno"}])
        with pytest.raises(ValueError, match="identidad estable"):
            school_roster.synchronize_roster(db, changed)
        db.rollback()
        changed = roster()
        changed["sections"][0]["grade"] = "2°"
        with pytest.raises(ValueError, match="identidad estable"):
            school_roster.synchronize_roster(db, changed, update_existing=True)
        db.rollback()
        assert db.get(Student, student_id).last_name == "Ejemplo"


@pytest.mark.parametrize("students", [["Nuevo, Dos", "inválido"], ["Nuevo, Dos", "Nuevo, Dos"]])
def test_error_rolls_back_entire_import(sessions, students):
    with sessions() as db:
        with pytest.raises(ValueError):
            with db.begin():
                school_roster.synchronize_roster(db, roster(students))
        assert db.scalar(select(Student)) is None
        assert db.scalar(select(AcademicPeriod)) is None


def test_ambiguous_names_rejected(sessions):
    with sessions() as db:
        db.add_all(
            [
                Student(first_name="Uno", last_name="Ejemplo"),
                Student(first_name="Uno", last_name="Ejemplo"),
            ]
        )
        db.commit()
        with pytest.raises(ValueError, match="ambigua"):
            school_roster.synchronize_roster(db, roster())
        db.rollback()


def test_command_preview_and_confirmed_apply(sessions, tmp_path, monkeypatch, capsys):
    from app import import_roster

    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(roster()), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(import_roster, "SessionLocal", sessions)
    monkeypatch.setattr("sys.argv", ["import_roster", "--path", str(path)])
    import_roster.main()
    assert json.loads(capsys.readouterr().out)["applied"] is False
    with sessions() as db:
        assert db.scalar(select(Student)) is None
    monkeypatch.setattr(
        "sys.argv", ["import_roster", "--path", str(path), "--apply", "--sha256", digest]
    )
    import_roster.main()
    assert json.loads(capsys.readouterr().out)["applied"] is True
    with sessions() as db:
        assert db.scalar(select(Student)).first_name == "Uno"


def test_command_rejects_changed_file_before_opening_database(tmp_path, monkeypatch):
    from app import import_roster

    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(roster()), encoding="utf-8")

    def forbidden():
        pytest.fail("A mismatched confirmation must not access the database")

    monkeypatch.setattr(import_roster, "SessionLocal", forbidden)
    monkeypatch.setattr(
        "sys.argv", ["import_roster", "--path", str(path), "--apply", "--sha256", "outdated"]
    )
    with pytest.raises(SystemExit) as error:
        import_roster.main()
    assert error.value.code == 2


def test_empty_roster_preserves_manual_records_and_does_not_enroll_them(sessions):
    with sessions() as db:
        school_roster.synchronize_roster(db, roster())
        section = db.scalar(select(Section))
        manual = Student(
            student_code="2026-001",
            first_name="Manual",
            last_name="Sintético",
            grade_id=section.grade_id,
            section_id=section.id,
            status="ACTIVE",
        )
        course = Course(name="Curso manual", code="CUSTOM", is_active=True)
        db.add_all([manual, course])
        db.flush()
        assignment = CourseAssignment(
            course_id=course.id,
            grade_id=section.grade_id,
            section_id=section.id,
            teacher_name="Asignación manual",
        )
        db.add(assignment)
        db.commit()
        manual_id, course_id, assignment_id = manual.id, course.id, assignment.id
        assert not any(school_roster.synchronize_roster(db, roster([], [])).values())
        school_roster.synchronize_roster(db, roster(courses=[{"name": "Curso nuevo"}]))
        db.commit()
        assert db.get(Student, manual_id).status == "ACTIVE"
        assert db.get(Student, manual_id).student_code == "2026-001"
        assert db.get(Course, course_id).is_active
        assert db.get(CourseAssignment, assignment_id).teacher_name == "Asignación manual"
        assert db.scalar(select(Enrollment).where(Enrollment.student_id == manual_id)) is None


def test_command_failed_apply_rolls_back_and_does_not_print_private_data(
    sessions,
    tmp_path,
    monkeypatch,
    capsys,
):
    from app import import_roster

    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(roster(["PrivadoSintético, Ejemplo", "invalid"])), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(import_roster, "SessionLocal", sessions)
    monkeypatch.setattr(
        "sys.argv",
        ["import_roster", "--path", str(path), "--apply", "--sha256", digest],
    )
    with pytest.raises(SystemExit) as error:
        import_roster.main()
    assert error.value.code == 1
    output = capsys.readouterr()
    assert "PrivadoSintético" not in output.out + output.err
    with sessions() as db:
        assert db.scalar(select(Student)) is None
        assert db.scalar(select(AcademicPeriod)) is None


@pytest.mark.parametrize(
    "reference",
    [
        {"student_code": "UNKNOWN"},
        {"id": "00000000-0000-0000-0000-000000000001"},
    ],
)
def test_unknown_identity_never_creates_a_replacement_student(sessions, reference):
    with sessions() as db:
        with pytest.raises(ValueError, match="identificador"):
            school_roster.synchronize_roster(
                db,
                roster([{**reference, "first_name": "Uno", "last_name": "Ejemplo"}]),
                update_existing=True,
            )
        db.rollback()
        assert db.scalar(select(Student)) is None


def test_failed_history_write_rolls_back_without_affecting_existing_history(sessions):
    student_id, record_ids = seed_history(sessions)
    with sessions() as db:
        course = db.scalar(select(Course))
        period = db.scalar(select(AcademicPeriod))
        db.add(
            GradeRecord(
                student_id=uuid4(),
                course_id=course.id,
                period_id=period.id,
                score=12,
                assessment_date=date(2026, 10, 1),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert_history(db, student_id, record_ids)
        assert len(db.scalars(select(GradeRecord)).all()) == 1
