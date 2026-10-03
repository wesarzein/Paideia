from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AcademicPeriod, Course, CourseAssignment, Enrollment, Grade, Section
from app.models.student import Student
from app.models.user import User
from app.core.academic_rules import LITERAL_GRADE_THRESHOLDS

router = APIRouter()


@router.get("/catalog")
def academic_catalog(
    grade_id: UUID | None = None,
    section_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator", "director", "student", "parent")),
) -> dict[str, list[dict[str, str | float | None]]]:
    grades = db.scalars(select(Grade).where(Grade.is_active.is_(True)).order_by(Grade.level, Grade.name)).all()
    section_query = select(Section).where(Section.is_active.is_(True))
    if grade_id:
        section_query = section_query.where(Section.grade_id == grade_id)
    sections = db.scalars(section_query.order_by(Section.name)).all()
    course_query = select(Course).where(Course.is_active.is_(True))
    if user.role.code == "teacher":
        teacher_assignments = select(CourseAssignment.course_id).where(CourseAssignment.teacher_id == user.id)
        if grade_id:
            teacher_assignments = teacher_assignments.where(CourseAssignment.grade_id == grade_id)
        if section_id:
            teacher_assignments = teacher_assignments.where(CourseAssignment.section_id == section_id)
        course_query = course_query.where(Course.id.in_(teacher_assignments))
    elif grade_id and section_id:
        assigned_course_ids = select(CourseAssignment.course_id).where(
            CourseAssignment.grade_id == grade_id,
            CourseAssignment.section_id == section_id,
        )
        enrolled_course_ids = select(Enrollment.course_id).join(Student, Student.id == Enrollment.student_id).where(
            Student.grade_id == grade_id,
            Student.section_id == section_id,
            Enrollment.status == "ACTIVE",
        )
        course_query = course_query.where(Course.id.in_(assigned_course_ids.union(enrolled_course_ids)))
    courses = db.scalars(course_query.order_by(Course.name)).all()
    periods = db.scalars(select(AcademicPeriod).where(AcademicPeriod.name == "Año escolar 2026").order_by(AcademicPeriod.starts_on)).all()
    students = []
    if grade_id and section_id:
        student_query = select(Student).where(
            Student.status == "ACTIVE",
            Student.grade_id == grade_id,
            Student.section_id == section_id,
        )
        if user.role.code == "teacher":
            authorized_section = select(CourseAssignment.id).where(
                CourseAssignment.grade_id == grade_id,
                CourseAssignment.section_id == section_id,
                CourseAssignment.teacher_id == user.id,
            )
            student_query = student_query.where(authorized_section.exists())
        elif user.role.code == "student":
            student_query = student_query.where(Student.student_user_id == user.id)
        elif user.role.code == "parent":
            student_query = student_query.where(Student.parent_user_id == user.id)
        students = db.scalars(student_query.order_by(Student.student_code, Student.last_name, Student.first_name)).all()
    return {
        "grades": [{"id": str(item.id), "name": item.name, "level": item.level} for item in grades],
        "sections": [{"id": str(item.id), "name": item.name, "grade_id": str(item.grade_id)} for item in sections],
        "courses": [{"id": str(item.id), "name": item.name, "code": item.code} for item in courses],
        "periods": [{"id": str(item.id), "name": item.name} for item in periods],
        "literal_scale": [{"greater_than": threshold, "grade": label} for threshold, label in LITERAL_GRADE_THRESHOLDS],
        "students": [
            {"id": str(item.id), "student_code": item.student_code, "name": f"{item.last_name}, {item.first_name}"}
            for item in students
        ],
    }