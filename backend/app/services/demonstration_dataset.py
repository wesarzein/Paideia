"""Seeded fictional academic history, only for a fresh isolated demo schema."""

import random
from datetime import date, timedelta
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import func, select, text

from app.models.academic import (
    AcademicPeriod,
    AttendanceRecord,
    Course,
    Enrollment,
    Grade,
    GradeRecord,
    Section,
)
from app.models.student import Student
from app.services.academic_metrics import academic_metrics
from app.services.risk_features import historical_features


def populate_demonstration(db, seed=42, pupils=80):
    if db.bind.dialect.name == "postgresql":
        schema = db.scalar(text("SELECT current_schema()"))
        if not schema.startswith(("ai_demo_", "phase2_")):
            raise ValueError("Demo data require an isolated synthetic schema")
    if db.scalar(select(func.count()).select_from(Student)):
        raise ValueError("Demo seeding requires an empty isolated schema")
    rng = random.Random(seed)

    def identity(key):
        return uuid5(NAMESPACE_URL, f"paideia-fictional:{seed}:{key}")

    grade = Grade(id=identity("grade"), name="Grupo demostrativo", level="Sintético")
    section = Section(id=identity("section"), grade_id=grade.id, name="DEMO")
    courses = [
        Course(id=identity(f"course:{i}"), name=name, code=f"DEMO-{i}")
        for i, name in enumerate(
            ("Computación ficticia", "Matemática ficticia", "Comunicación ficticia")
        )
    ]
    periods = [
        AcademicPeriod(
            id=identity(f"period:{i}"),
            name=f"Periodo ficticio {i + 1}",
            starts_on=date(2020, 1 + 2 * i, 1),
            ends_on=date(2020, 1 + 2 * i, 1) + timedelta(days=44),
        )
        for i in range(5)
    ]
    db.add_all([grade, *courses, *periods])
    db.flush()
    db.add(section)
    students = [
        Student(
            id=identity(f"student:{i}"),
            student_code=f"DEMO-{i:04}",
            first_name="Estudiante ficticio",
            last_name=f"Demo {i:04}",
            grade_id=grade.id,
            section_id=section.id,
        )
        for i in range(pupils)
    ]
    db.add_all(students)
    db.flush()
    for i, student in enumerate(students):
        base = rng.uniform(5, 19)
        trend = (-1, 0, 1)[i % 3] * rng.uniform(0.2, 1)
        for j, period in enumerate(periods):
            for k, course in enumerate(courses):
                db.add(Enrollment(student_id=student.id, course_id=course.id, period_id=period.id))
                # Includes insufficient histories and partially recorded evidence.
                if i % 13 == 0 and j < 3:
                    continue
                for n in range(1 if i % 7 == 0 else 3):
                    score = max(0, min(20, base + trend * j + k * 0.3 + rng.gauss(0, 2)))
                    if i == 1 and j == 0 and n == 0:
                        score = 0
                    db.add(
                        GradeRecord(
                            student_id=student.id,
                            course_id=course.id,
                            period_id=period.id,
                            evaluation_name=f"Ficticia {n}",
                            assessment_date=period.starts_on + timedelta(days=7 + n),
                            academic_bimester=j + 1,
                            score=round(score, 2),
                        )
                    )
                for day in range(6):
                    probability = max(0.2, min(0.98, 0.45 + base / 40))
                    status = (
                        "PRESENT"
                        if rng.random() < probability
                        else rng.choice(["ABSENT", "ABSENT", "LATE"])
                    )
                    db.add(
                        AttendanceRecord(
                            student_id=student.id,
                            course_id=course.id,
                            period_id=period.id,
                            status=status,
                            attendance_date=period.starts_on + timedelta(days=day),
                        )
                    )
    db.commit()
    return {
        "seed": seed,
        "pupils": pupils,
        "courses": len(courses),
        "periods": len(periods),
        "source": "fictional_seeded_academic_records",
        "personal_data": False,
    }


def labeled_examples(db, failure_cutoff=10.4):
    grades = db.scalars(select(GradeRecord)).all()
    attendance = db.scalars(select(AttendanceRecord)).all()
    periods = db.scalars(select(AcademicPeriod).order_by(AcademicPeriod.starts_on)).all()
    examples = []
    for index, period in enumerate(periods):
        for row in historical_features(grades, attendance, periods, period.id):
            target_rows = [
                g
                for g in grades
                if str(g.student_id) == row["student_id"]
                and str(g.course_id) == row["course_id"]
                and g.period_id == period.id
            ]
            target = academic_metrics(target_rows, []).average_score
            row["target"] = int(target <= failure_cutoff) if target is not None else None
            row["target_index"] = index
            examples.append(row)
    return examples
