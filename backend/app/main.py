import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date

from sqlalchemy import select, text

from app.api.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import Role, User
from app.models.academic import AcademicPeriod, Course, Enrollment, Grade, Section
from app.models.student import Student

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        version=settings.api_version,
        description="API para seguimiento y prevencion del riesgo academico institucional.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.on_event("startup")
    def synchronize_demo_admin() -> None:
        with SessionLocal() as db:
            db.execute(text("ALTER TABLE students ADD COLUMN IF NOT EXISTS grade_id UUID"))
            db.execute(text("ALTER TABLE students ADD COLUMN IF NOT EXISTS section_id UUID"))
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS enrollments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    student_id UUID NOT NULL REFERENCES students(id),
                    course_id UUID NOT NULL REFERENCES courses(id),
                    period_id UUID NOT NULL REFERENCES academic_periods(id),
                    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            db.execute(text("CREATE TABLE IF NOT EXISTS follow_ups (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL REFERENCES students(id), status VARCHAR(30) NOT NULL DEFAULT 'OPEN', action VARCHAR(500) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"))
            role = db.scalar(select(Role).where(Role.code == "admin"))
            if role is None:
                role = Role(code="admin", name="Administrador")
                db.add(role)
                db.flush()
            user = db.scalar(select(User).where(User.email == "admin@paideia.local"))
            if user is None:
                user = User(
                    email="admin@paideia.local",
                    full_name="Administrador Demo",
                    password_hash=hash_password("Admin123!"),
                    role_id=role.id,
                )
                db.add(user)
            else:
                user.role_id = role.id
                user.password_hash = hash_password("Admin123!")
            demo_grades = []
            for name, level in (("Cuarto", "Primaria"), ("Quinto", "Primaria"), ("Sexto", "Primaria"), ("Primero", "Secundaria"), ("Segundo", "Secundaria"), ("Tercero", "Secundaria"), ("Cuarto", "Secundaria"), ("Quinto", "Secundaria")):
                grade = db.scalar(select(Grade).where(Grade.name == name, Grade.level == level))
                if grade is None:
                    grade = Grade(name=name, level=level)
                    db.add(grade)
                    db.flush()
                demo_grades.append(grade)
                section_names = ["A", "B"] if name in ("Primero", "Tercero") and level == "Secundaria" else ["A"]
                for section_name in section_names:
                    if db.scalar(select(Section).where(Section.grade_id == grade.id, Section.name == section_name)) is None:
                        db.add(Section(grade_id=grade.id, name=section_name))
            if db.scalar(select(AcademicPeriod).where(AcademicPeriod.name == "Año escolar 2026")) is None:
                db.add(AcademicPeriod(name="Año escolar 2026", starts_on=date(2026, 3, 1), ends_on=date(2026, 12, 20)))
            for name, code in (("Matemática", "MAT-01"), ("Comunicación", "COM-01"), ("Ciencia y Tecnología", "CT-01"), ("Ciencias Sociales", "CS-01")):
                if db.scalar(select(Course).where(Course.code == code)) is None:
                    db.add(Course(name=name, code=code))
            db.flush()
            school_period = db.scalar(select(AcademicPeriod).where(AcademicPeriod.name == "Año escolar 2026"))
            demo_courses = db.scalars(select(Course).order_by(Course.code)).all()
            first_grade = demo_grades[0]
            first_section = db.scalar(select(Section).where(Section.grade_id == first_grade.id, Section.name == "A"))
            demo_names = (("Ana", "Quispe"), ("Bruno", "Salazar"), ("Camila", "Torres"), ("Diego", "Ramos"), ("Elena", "Mendoza"), ("Fabian", "Cruz"), ("Gabriela", "Flores"), ("Hugo", "Paredes"), ("Irene", "Castillo"), ("Joaquin", "Vargas"))
            for index, (first_name, last_name) in enumerate(demo_names, 1):
                code = f"2026-{index:03d}"
                student = db.scalar(select(Student).where(Student.student_code == code))
                if student is None:
                    student = Student(student_code=code, first_name=first_name, last_name=last_name, grade_id=first_grade.id, section_id=first_section.id if first_section else None)
                    db.add(student)
                    db.flush()
                else:
                    student.grade_id = first_grade.id
                    student.section_id = first_section.id if first_section else None
                if school_period:
                    for course in demo_courses:
                        exists = db.scalar(select(Enrollment).where(Enrollment.student_id == student.id, Enrollment.course_id == course.id, Enrollment.period_id == school_period.id))
                        if exists is None:
                            db.add(Enrollment(student_id=student.id, course_id=course.id, period_id=school_period.id, status="ACTIVE"))
            db.commit()

    return app


app = create_app()
