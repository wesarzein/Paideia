"""Explicit, additive roster import. The caller owns commit/rollback."""

import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.base import (
    AcademicPeriod,
    Course,
    CourseAssignment,
    Enrollment,
    Grade,
    Section,
    Student,
)
from app.services.course_catalog import canonical_course_name, unique_course_code
from app.services.student_codes import format_student_code, student_code_prefix

ROSTER_PATH = Path("/app/local-data/roster.json")


def _key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", normalized)


def load_roster(path: Path = ROSTER_PATH) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as roster_file:
        data = json.load(roster_file)
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("sections"), list)
        or not data["sections"]
    ):
        raise ValueError("El padrón debe contener una lista no vacía de secciones")
    return data


def _student_names(raw: Any) -> tuple[str, str]:
    if isinstance(raw, str):
        surname, separator, given = raw.partition(",")
        if not separator:
            raise ValueError("Un estudiante debe tener formato 'APELLIDOS, NOMBRES'")
    elif isinstance(raw, dict):
        surname, given = raw.get("last_name"), raw.get("first_name")
    else:
        raise ValueError("Formato de estudiante no válido")
    if (
        not isinstance(surname, str)
        or not isinstance(given, str)
        or not surname.strip()
        or not given.strip()
    ):
        raise ValueError("Cada estudiante requiere apellidos y nombres")
    return surname.strip(), given.strip()


def _resolve_student(db: Session, raw: Any, surname: str, given: str) -> Student | None:
    if isinstance(raw, dict) and (raw.get("id") or raw.get("student_code")):
        student = (
            db.get(Student, UUID(str(raw["id"])))
            if raw.get("id")
            else db.scalar(select(Student).where(Student.student_code == raw["student_code"]))
        )
        if student is None:
            raise ValueError("El identificador indicado no corresponde a un estudiante existente")
        if raw.get("student_code") and student.student_code != raw["student_code"]:
            raise ValueError("El UUID y el código de estudiante no coinciden")
        return student
    matches = [
        item
        for item in db.scalars(select(Student)).all()
        if _key(f"{item.last_name}, {item.first_name}") == _key(f"{surname}, {given}")
    ]
    if len(matches) > 1:
        raise ValueError("Identidad ambigua; indique UUID o código estable del estudiante")
    return matches[0] if matches else None


def _new_student_code(db: Session, grade: Grade, section: Section) -> str:
    prefix = student_code_prefix(grade, section)
    codes = db.scalars(select(Student.student_code).where(Student.student_code.like(f"{prefix}%")))
    suffixes = [
        int(code[len(prefix) :]) for code in codes if code and code[len(prefix) :].isdigit()
    ]
    return format_student_code(grade, section, max(suffixes, default=0) + 1)


def synchronize_roster(
    db: Session,
    roster: dict[str, Any],
    *,
    update_existing: bool = False,
) -> dict[str, int]:
    """Add missing entries; update student names/group only with explicit identity and opt-in.

    Absence never means withdrawal. Existing codes, status, courses, assignments,
    enrollments, assessments and histories are never reset. Errors must roll back
    the entire transaction, including additions flushed before the error.
    """
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(20261008)"))
    school_year = int(roster["school_year"])
    sections = roster.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("El padrón debe contener secciones")
    counts = dict.fromkeys(
        ("sections", "students", "courses", "assignments", "enrollments", "updated_students"), 0
    )
    period_name = f"Año escolar {school_year}"
    periods = db.scalars(select(AcademicPeriod).where(AcademicPeriod.name == period_name)).all()
    if len(periods) > 1:
        raise ValueError("Periodo ambiguo; concilie el catálogo antes de importar")
    period = periods[0] if periods else None
    if period is None:
        period = AcademicPeriod(
            name=period_name, starts_on=date(school_year, 1, 1), ends_on=date(school_year, 12, 31)
        )
        db.add(period)
        db.flush()
    seen_students: set[UUID] = set()
    for section_data in sections:
        level, grade_name, section_name = (
            str(section_data[key]).strip() for key in ("level", "grade", "section")
        )
        if not all((level, grade_name, section_name)):
            raise ValueError("Nivel, grado y sección son obligatorios")
        grade = db.scalars(
            select(Grade).where(Grade.level == level, Grade.name == grade_name)
        ).one_or_none()
        if grade is None:
            grade = Grade(level=level, name=grade_name)
            db.add(grade)
            db.flush()
        section = db.scalars(
            select(Section).where(Section.grade_id == grade.id, Section.name == section_name)
        ).one_or_none()
        if section is None:
            section = Section(grade_id=grade.id, name=section_name)
            db.add(section)
            db.flush()
            counts["sections"] += 1
        imported_students = []
        for raw in section_data.get("students", []):
            surname, given = _student_names(raw)
            student = _resolve_student(db, raw, surname, given)
            if student is None:
                student = Student(
                    student_code=_new_student_code(db, grade, section),
                    last_name=surname,
                    first_name=given,
                    status="ACTIVE",
                    grade_id=grade.id,
                    section_id=section.id,
                )
                db.add(student)
                db.flush()
                counts["students"] += 1
            else:
                explicit_identity = isinstance(raw, dict) and (
                    raw.get("id") or raw.get("student_code")
                )
                changed = (
                    student.last_name,
                    student.first_name,
                    student.grade_id,
                    student.section_id,
                ) != (surname, given, grade.id, section.id)
                if changed and not (update_existing and explicit_identity):
                    raise ValueError(
                        "Cambio de estudiante requiere identidad estable y --update-existing"
                    )
                if changed:
                    student.last_name, student.first_name = surname, given
                    student.grade_id, student.section_id = grade.id, section.id
                    counts["updated_students"] += 1
            if student.id in seen_students:
                raise ValueError("Estudiante repetido en el padrón; concilie antes de importar")
            seen_students.add(student.id)
            imported_students.append(student)
        db.flush()
        imported_courses = []
        for course_data in section_data.get("courses", []):
            course_name = canonical_course_name(str(course_data["name"]))
            if not course_name:
                raise ValueError("El curso requiere un nombre")
            matches = [
                item
                for item in db.scalars(select(Course)).all()
                if _key(item.name) == _key(course_name)
            ]
            if len(matches) > 1:
                raise ValueError("Curso ambiguo; concilie el catálogo antes de importar")
            course = matches[0] if matches else None
            if course is None:
                course = Course(
                    name=course_name, code=unique_course_code(db, course_name), is_active=True
                )
                db.add(course)
                db.flush()
                counts["courses"] += 1
            assignment = db.scalar(
                select(CourseAssignment).where(
                    CourseAssignment.course_id == course.id,
                    CourseAssignment.section_id == section.id,
                )
            )
            if assignment is None:
                db.add(
                    CourseAssignment(
                        course_id=course.id,
                        grade_id=grade.id,
                        section_id=section.id,
                        teacher_id=None,
                        teacher_name=course_data.get("teacher"),
                    )
                )
                db.flush()
                counts["assignments"] += 1
            imported_courses.append(course)
        for student in imported_students:
            if student.status != "ACTIVE" or not grade.is_active or not section.is_active:
                continue
            for course in imported_courses:
                if not course.is_active:
                    continue
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
                    db.flush()
                    counts["enrollments"] += 1
    db.flush()
    return counts
