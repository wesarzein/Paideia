import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models.academic import AcademicPeriod, AttendanceRecord, Course, CourseAssignment, Enrollment, Grade, GradeRecord, Section
from app.models.follow_up import FollowUp
from app.models.student import Student
from app.services.course_catalog import canonical_course_name, unique_course_code
from app.services.student_codes import format_student_code

ROSTER_PATH = Path("/app/local-data/roster.json")


def _key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", normalized)


def load_roster(path: Path = ROSTER_PATH) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as roster_file:
        data = json.load(roster_file)
    if not isinstance(data.get("sections"), list) or not data["sections"]:
        raise ValueError("El padrón local no contiene secciones")
    return data


def synchronize_roster(db: Session, roster: dict[str, Any]) -> dict[str, int]:
    wanted_students: set[UUID] = set()
    wanted_courses: dict[str, Course] = {}
    wanted_assignments: set[tuple[str, str]] = set()
    wanted_grade_sections: set[tuple[str, str, str]] = set()

    school_year = int(roster["school_year"])
    period_name = f"Año escolar {school_year}"
    period = db.scalar(select(AcademicPeriod).where(AcademicPeriod.name == period_name))
    if period is None:
        period = AcademicPeriod(name=period_name, starts_on=date(school_year, 1, 1), ends_on=date(school_year, 12, 31))
        db.add(period)
        db.flush()

    seeded_students = db.scalars(select(Student).where(Student.student_code.in_(["STU-1001", *[f"2026-{index:03d}" for index in range(1, 11)]]))).all()
    for seeded in seeded_students:
        db.execute(delete(FollowUp).where(FollowUp.student_id == seeded.id))
        db.execute(delete(GradeRecord).where(GradeRecord.student_id == seeded.id))
        db.execute(delete(AttendanceRecord).where(AttendanceRecord.student_id == seeded.id))
        db.execute(delete(Enrollment).where(Enrollment.student_id == seeded.id))
        db.delete(seeded)

    sections_in_source: list[tuple[dict[str, Any], Grade, Section]] = []
    for section_data in roster["sections"]:
        level = str(section_data["level"]).strip()
        grade_name = str(section_data["grade"]).strip()
        section_name = str(section_data["section"]).strip()
        grade = db.scalar(select(Grade).where(Grade.level == level, Grade.name == grade_name))
        if grade is None:
            grade = Grade(level=level, name=grade_name)
            db.add(grade)
            db.flush()
        section = db.scalar(select(Section).where(Section.grade_id == grade.id, Section.name == section_name))
        if section is None:
            section = Section(grade_id=grade.id, name=section_name)
            db.add(section)
            db.flush()
        wanted_grade_sections.add((level, grade_name, section_name))
        sections_in_source.append((section_data, grade, section))

    db.flush()
    wanted_grade_ids = {grade.id for _, grade, _ in sections_in_source}
    wanted_section_ids = {section.id for _, _, section in sections_in_source}
    for grade in db.scalars(select(Grade)).all():
        grade.is_active = grade.id in wanted_grade_ids
    for section in db.scalars(select(Section)).all():
        section.is_active = section.id in wanted_section_ids
    known_students = db.scalars(select(Student)).all()
    roster_student_keys = {
        _key(str(raw_name))
        for section_data, _, _ in sections_in_source
        for raw_name in section_data.get("students", [])
    }
    for known_student in known_students:
        if _key(f"{known_student.last_name}, {known_student.first_name}") in roster_student_keys:
            known_student.student_code = None
    db.flush()
    for section_data, grade, section in sections_in_source:
        for order, raw_name in enumerate(section_data.get("students", []), start=1):
            surname, separator, given = str(raw_name).partition(",")
            if not separator or not surname.strip() or not given.strip():
                raise ValueError(f"Nombre de padrón debe tener formato 'APELLIDOS, NOMBRES': {raw_name}")
            full_key = _key(f"{surname.strip()}, {given.strip()}")
            student = next(
                (
                    item
                    for item in known_students
                    if item.grade_id == grade.id
                    and item.section_id == section.id
                    and _key(f"{item.last_name}, {item.first_name}") == full_key
                ),
                None,
            )
            if student is None:
                matching_students = [
                    item
                    for item in known_students
                    if _key(f"{item.last_name}, {item.first_name}") == full_key
                ]
                if len(matching_students) == 1:
                    student = matching_students[0]
            if student is None:
                student = Student(student_code=format_student_code(grade, section, order), last_name=surname.strip(), first_name=given.strip(), status="ACTIVE", grade_id=grade.id, section_id=section.id)
                db.add(student)
                db.flush()
                known_students.append(student)
            else:
                student.student_code = format_student_code(grade, section, order)
                student.last_name = surname.strip()
                student.first_name = given.strip()
                student.status = "ACTIVE"
                student.grade_id = grade.id
                student.section_id = section.id
            wanted_students.add(student.id)

        for course_data in section_data.get("courses", []):
            course_name = canonical_course_name(str(course_data["name"]))
            course_key = _key(course_name)
            course = wanted_courses.get(course_key)
            if course is None:
                course = next((item for item in db.scalars(select(Course)).all() if _key(item.name) == course_key), None)
                if course is None:
                    course = Course(name=course_name, code=unique_course_code(db, course_name), is_active=True)
                    db.add(course)
                    db.flush()
                else:
                    course.name = course_name
                    if not course.code:
                        course.code = unique_course_code(db, course_name)
                    course.is_active = True
                wanted_courses[course_key] = course
            assignment = db.scalar(select(CourseAssignment).where(CourseAssignment.course_id == course.id, CourseAssignment.section_id == section.id))
            teacher_name = course_data.get("teacher")
            if assignment is None:
                assignment = CourseAssignment(course_id=course.id, grade_id=grade.id, section_id=section.id, teacher_id=None, teacher_name=teacher_name)
                db.add(assignment)
            else:
                assignment.grade_id = grade.id
                assignment.teacher_name = teacher_name
            wanted_assignments.add((str(course.id), str(section.id)))

    db.flush()
    desired_course_uuids = [course.id for course in wanted_courses.values()]
    stale_students = (
        db.scalars(select(Student).where(Student.id.not_in(wanted_students))).all()
        if wanted_students
        else db.scalars(select(Student)).all()
    )
    stale_student_ids = [student.id for student in stale_students]
    for student in stale_students:
        student.status = "INACTIVE"
    if stale_student_ids:
        db.execute(
            update(Enrollment)
            .where(Enrollment.student_id.in_(stale_student_ids))
            .values(status="INACTIVE")
        )

    for assignment in db.scalars(select(CourseAssignment)).all():
        if (str(assignment.course_id), str(assignment.section_id)) not in wanted_assignments:
            db.delete(assignment)

    stale_courses = db.scalars(select(Course).where(Course.id.not_in(desired_course_uuids))).all() if desired_course_uuids else db.scalars(select(Course)).all()
    stale_course_ids = [course.id for course in stale_courses]
    for course in stale_courses:
        course.is_active = False
    if stale_course_ids:
        db.execute(
            update(Enrollment)
            .where(Enrollment.course_id.in_(stale_course_ids))
            .values(status="INACTIVE")
        )

    for _, grade, section in sections_in_source:
        student_ids = [student.id for student in db.scalars(select(Student).where(Student.grade_id == grade.id, Student.section_id == section.id, Student.status == "ACTIVE")).all()]
        course_ids = [course.id for course in wanted_courses.values() if db.scalar(select(CourseAssignment.id).where(CourseAssignment.course_id == course.id, CourseAssignment.section_id == section.id))]
        for student_id in student_ids:
            for course_id in course_ids:
                enrollment = db.scalar(select(Enrollment).where(Enrollment.student_id == student_id, Enrollment.course_id == course_id, Enrollment.period_id == period.id))
                if enrollment is None:
                    db.add(Enrollment(student_id=student_id, course_id=course_id, period_id=period.id, status="ACTIVE"))
                else:
                    enrollment.status = "ACTIVE"
    db.commit()
    return {"sections": len(wanted_grade_sections), "students": len(wanted_students), "courses": len(wanted_courses), "assignments": len(wanted_assignments)}
