from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.models.academic import AcademicPeriod, Course
from app.models.student import Student
from app.models.user import Role, User


def _seed_basics() -> None:
    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.code == "admin"))
        if role is None:
            db.add(Role(code="admin", name="Administrador"))
            db.add(Role(code="teacher", name="Docente"))
            db.add(Role(code="coordinator", name="Coordinador"))
            db.add(Role(code="director", name="Directivo"))
            db.add(Role(code="student", name="Estudiante"))
            db.add(Role(code="parent", name="Padre de familia"))
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
                    starts_on="2026-03-01",
                    ends_on="2026-07-31",
                )
            )
        db.commit()


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


def test_grade_value_must_be_in_official_scale() -> None:
    _seed_basics()
    client = TestClient(app)

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
    )

    assert response.status_code == 422
    assert "0 y 20" in response.json()["detail"][0]["msg"] or "0 and 20" in response.json()["detail"][0]["msg"]


def test_attendance_record_is_created() -> None:
    _seed_basics()
    client = TestClient(app)

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
    )

    assert response.status_code == 201
    assert response.json()["status"] == "PRESENT"
