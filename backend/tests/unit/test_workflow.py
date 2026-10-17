from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from test_roster_persistence import sessions

from app.core.database import SessionLocal, get_db
from app.core.security import hash_password
from app.main import app
from app.models.academic import (
    AcademicPeriod,
    AttendanceRecord,
    Course,
    CourseAssessmentComponent,
    CourseAssignment,
    Enrollment,
    Grade,
    GradeRecord,
    Section,
)
from app.models.follow_up import FollowUp
from app.models.student import Student
from app.models.user import Role, User
from app.services.student_codes import format_student_code

__all__ = ["sessions"]


def test_school_student_code_format() -> None:
    primary_grade = Grade(name="5°", level="Primaria")
    primary_section = Section(name="A", grade_id="00000000-0000-0000-0000-000000000001")
    secondary_grade = Grade(name="1°", level="Secundaria")
    secondary_section = Section(name="B", grade_id="00000000-0000-0000-0000-000000000002")

    assert format_student_code(primary_grade, primary_section, 1) == "5P001"
    assert format_student_code(secondary_grade, secondary_section, 1) == "1SB001"


def _cleanup_test_data() -> None:
    with SessionLocal() as db:
        student = db.scalar(select(Student).where(Student.student_code == "STU-1001"))
        course = db.scalar(select(Course).where(Course.code == "MAT-01"))
        period = db.scalar(select(AcademicPeriod).where(AcademicPeriod.name == "2026-I"))
        if student is not None:
            db.execute(delete(FollowUp).where(FollowUp.student_id == student.id))
            db.execute(delete(GradeRecord).where(GradeRecord.student_id == student.id))
            db.execute(delete(AttendanceRecord).where(AttendanceRecord.student_id == student.id))
            db.execute(delete(Enrollment).where(Enrollment.student_id == student.id))
            db.delete(student)
        if course is not None:
            db.execute(delete(CourseAssignment).where(CourseAssignment.course_id == course.id))
            db.execute(
                delete(CourseAssessmentComponent).where(
                    CourseAssessmentComponent.course_id == course.id
                )
            )
            db.execute(delete(GradeRecord).where(GradeRecord.course_id == course.id))
            db.execute(delete(AttendanceRecord).where(AttendanceRecord.course_id == course.id))
            db.execute(delete(Enrollment).where(Enrollment.course_id == course.id))
            db.delete(course)
        if period is not None:
            db.execute(delete(GradeRecord).where(GradeRecord.period_id == period.id))
            db.execute(delete(AttendanceRecord).where(AttendanceRecord.period_id == period.id))
            db.execute(delete(Enrollment).where(Enrollment.period_id == period.id))
            db.delete(period)
        test_admin = db.scalar(
            select(User).where(
                User.email == "admin@paideia.local",
                User.full_name == "Administrador Demo",
            )
        )
        if test_admin is not None:
            db.delete(test_admin)
        db.commit()


@pytest.fixture(autouse=True)
def clean_test_records(sessions, monkeypatch):
    from app import main

    # Even the legacy helpers must use the guarded UUID/SQLite fixture, never the
    # globally configured database. Startup and API requests share that target.
    monkeypatch.setitem(globals(), 'SessionLocal', sessions)
    monkeypatch.setattr(main, 'SessionLocal', sessions)
    def database():
        with sessions() as db:
            yield db
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = database
    _cleanup_test_data()
    try:
        yield
        _cleanup_test_data()
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


def _seed_basics() -> None:
    with SessionLocal() as db:
        for code, name in (
            ("admin", "Administrador"),
            ("teacher", "Docente"),
            ("coordinator", "Coordinador"),
            ("director", "Directivo"),
            ("student", "Estudiante"),
            ("parent", "Padre o apoderado"),
        ):
            if db.scalar(select(Role.id).where(Role.code == code)) is None:
                db.add(Role(code=code, name=name))
        db.flush()
        admin = db.scalar(select(User).where(User.email == "admin@paideia.local"))
        if admin is None:
            admin_role = db.scalar(select(Role).where(Role.code == "admin"))
            db.add(
                User(
                    email="admin@paideia.local",
                    password_hash=hash_password("Admin123!"),
                    full_name="Administrador Demo",
                    role_id=admin_role.id,
                )
            )

        student = db.scalar(select(Student).where(Student.student_code == "STU-1001"))
        if student is None:
            db.add(
                Student(
                    student_code="STU-1001",
                    first_name="Ana",
                    last_name="Pérez",
                    status="ACTIVE",
                )
            )

        course = db.scalar(select(Course).where(Course.code == "MAT-01"))
        if course is None:
            db.add(Course(name="Matemática", code="MAT-01"))

        period = db.scalar(select(AcademicPeriod).where(AcademicPeriod.name == "2026-I"))
        if period is None:
            db.add(
                AcademicPeriod(
                    name="2026-I",
                    starts_on=date(2026, 3, 1),
                    ends_on=date(2026, 7, 31),
                )
            )
        db.flush()
        student = db.scalar(select(Student).where(Student.student_code == "STU-1001"))
        course = db.scalar(select(Course).where(Course.code == "MAT-01"))
        period = db.scalar(select(AcademicPeriod).where(AcademicPeriod.name == "2026-I"))
        enrollment = db.scalar(
            select(Enrollment).where(
                Enrollment.student_id == student.id,
                Enrollment.course_id == course.id,
                Enrollment.period_id == period.id,
            )
        )
        if enrollment is None:
            db.add(
                Enrollment(
                    student_id=student.id,
                    course_id=course.id,
                    period_id=period.id,
                    status="ACTIVE",
                )
            )
        db.commit()


def _admin_headers() -> dict[str, str]:
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@paideia.local", "password": "Admin123!"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _actor_headers(role_code="teacher"):
    from app.endpoints.auth import _create_token

    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.code == role_code))
        actor = User(role_id=role.id, email=f"{role_code}-{uuid4().hex}@synthetic.invalid",
                     full_name="Responsable de prueba", password_hash="synthetic")
        db.add(actor)
        db.flush()
        if role_code == "teacher":
            grade = Grade(name="1", level="Secundaria")
            db.add(grade)
            db.flush()
            section = Section(grade_id=grade.id, name="A")
            db.add(section)
            db.flush()
            student = db.scalar(select(Student).where(Student.student_code == "STU-1001"))
            student.grade_id, student.section_id = grade.id, section.id
            course = db.scalar(select(Course).where(Course.code == "MAT-01"))
            db.add(CourseAssignment(course_id=course.id, grade_id=grade.id,
                                    section_id=section.id, teacher_id=actor.id))
        db.commit()
        return {"Authorization": "Bearer " + _create_token(actor)}


def test_login_returns_token() -> None:
    _seed_basics()
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@paideia.local", "password": "Admin123!"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "access_token" in payload
    assert payload["user"]["email"] == "admin@paideia.local"
    assert payload["user"]["role"] == "admin"


def test_users_list_serializes_role_code() -> None:
    _seed_basics()
    response = TestClient(app).get("/api/v1/users", headers=_admin_headers())

    assert response.status_code == 200
    assert response.json()
    assert all(isinstance(user["role"], str) for user in response.json())


@pytest.mark.parametrize("role_code", ["director", "student", "parent"])
def test_retired_account_roles_cannot_be_created(role_code) -> None:
    _seed_basics()
    email = f"retired-{uuid4().hex[:10]}@paideia.local"
    response = TestClient(app).post(
        "/api/v1/users",
        json={
            "email": email,
            "full_name": "Cuenta de rol retirado",
            "password": "SyntheticTest123!",
            "role_code": role_code,
        },
        headers=_admin_headers(),
    )
    assert response.status_code == 400
    with SessionLocal() as db:
        assert db.scalar(select(User.id).where(User.email == email)) is None


def test_grade_value_must_be_in_official_scale() -> None:
    _seed_basics()
    client = TestClient(app)
    headers = _actor_headers()

    student = SessionLocal().scalar(select(Student).where(Student.student_code == "STU-1001"))
    course = SessionLocal().scalar(select(Course).where(Course.code == "MAT-01"))
    period = SessionLocal().scalar(select(AcademicPeriod).where(AcademicPeriod.name == "2026-I"))

    response = client.post(
        "/api/v1/grades",
        json={
            "student_id": str(student.id),
            "course_id": str(course.id),
            "period_id": str(period.id),
            "score": 22,
            "qualitative_note": "Muy alta",
        },
        headers=headers,
    )

    assert response.status_code == 422
    detail = response.json()["detail"][0]["msg"]
    assert "less than or equal to 20" in detail or "greater than or equal to 0" in detail


def test_attendance_record_is_created() -> None:
    _seed_basics()
    client = TestClient(app)
    headers = _actor_headers()

    student = SessionLocal().scalar(select(Student).where(Student.student_code == "STU-1001"))
    course = SessionLocal().scalar(select(Course).where(Course.code == "MAT-01"))
    period = SessionLocal().scalar(select(AcademicPeriod).where(AcademicPeriod.name == "2026-I"))

    response = client.post(
        "/api/v1/attendance",
        json={
            "student_id": str(student.id),
            "course_id": str(course.id),
            "period_id": str(period.id),
            "status": "PRESENT",
            "attendance_date": "2026-04-15",
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["status"] == "PRESENT"


def test_grade_import_is_atomic_on_invalid_row() -> None:
    _seed_basics()
    client = TestClient(app)
    headers = _actor_headers()
    with SessionLocal() as db:
        student = db.scalar(select(Student).where(Student.student_code == "STU-1001"))
        course = db.scalar(select(Course).where(Course.code == "MAT-01"))
        period = db.scalar(select(AcademicPeriod).where(AcademicPeriod.name == "2026-I"))
        assert student is not None and course is not None and period is not None

    response = client.post(
        "/api/v1/imports/grades/commit",
        headers=headers,
        json={
            "course_id": str(course.id),
            "period_id": str(period.id),
            "rows": [
                {"student_code": "STU-1001", "score": 18, "assessment_date": "2026-04-15"},
                {"student_code": "STU-1001", "score": 22, "assessment_date": "2026-04-15"},
            ],
        },
    )

    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.scalar(
            select(GradeRecord.id).where(
                GradeRecord.student_id == student.id,
                GradeRecord.course_id == course.id,
                GradeRecord.period_id == period.id,
            )
        ) is None


def test_courses_hide_archived_by_default() -> None:
    _seed_basics()
    with SessionLocal() as db:
        archived = Course(
            name="Curso archivado de prueba", code="ARCHIVED-CHECK-01", is_active=False
        )
        db.add(archived)
        db.commit()
        archived_id = archived.id
    try:
        client = TestClient(app)
        headers = _admin_headers()
        active_response = client.get("/api/v1/courses", headers=headers)
        archived_response = client.get("/api/v1/courses?include_inactive=true", headers=headers)
        assert active_response.status_code == 200
        assert all(item["code"] != "ARCHIVED-CHECK-01" for item in active_response.json())
        assert any(item["code"] == "ARCHIVED-CHECK-01" for item in archived_response.json())
    finally:
        with SessionLocal() as db:
            item = db.get(Course, archived_id)
            if item is not None:
                db.delete(item)
                db.commit()


def test_business_indicators_enabled_without_institutional_ai() -> None:
    _seed_basics()
    client = TestClient(app)
    headers = _admin_headers()

    response = client.get("/api/v1/kpis", headers=headers)
    assert response.status_code == 200
    assert response.json()["ai"]["institutional_predictions"] is False
    model_status = client.get("/api/v1/risk-models", headers=headers)
    assert model_status.status_code == 200
    assert model_status.json()["institutional_status"] == "inactive_policy_and_data_required"
    assert model_status.json()["active_run_id"] is None
    prediction = client.get("/api/v1/risk-models/demonstration/predictions", headers=headers)
    assert prediction.status_code == 200
    assert prediction.json()["status"] == "untrained_or_inactive"
    assert prediction.json()["rows"] == []
    assert client.get("/api/v1/dashboard/risk-alerts", headers=headers).status_code == 501


def test_follow_up_requires_valid_student() -> None:
    _seed_basics()
    client = TestClient(app)
    headers = _actor_headers("coordinator")

    response = client.post(
        "/api/v1/follow-ups",
        json={
            "student_id": "11111111-1111-4111-8111-111111111111",
            "action": "Reunión con la familia para revisar riesgo académico.",
            "status": "OPEN",
        },
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Estudiante no encontrado"
