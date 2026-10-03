from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import CourseAssignment, Enrollment
from app.models.student import Student
from app.models.user import User


def ensure_student_course_access(
    db: Session,
    user: User,
    student: Student,
    course_id: UUID,
    period_id: UUID,
) -> None:
    assignment = db.scalar(
        select(CourseAssignment).where(
            CourseAssignment.course_id == course_id,
            CourseAssignment.grade_id == student.grade_id,
            CourseAssignment.section_id == student.section_id,
        )
    )
    if user.role.code == "teacher":
        if assignment is None or assignment.teacher_id != user.id:
            raise HTTPException(status_code=403, detail="No tienes asignado este curso y sección")
        return

    enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.course_id == course_id,
            Enrollment.period_id == period_id,
            Enrollment.status == "ACTIVE",
        )
    )
    if assignment is None and enrollment is None:
        raise HTTPException(status_code=409, detail="No existe asignación del curso a esta sección ni matrícula activa")


def ensure_student_view_access(user: User, student: Student) -> None:
    if user.role.code == "student" and student.student_user_id != user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este estudiante")
    if user.role.code == "parent" and student.parent_user_id != user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este estudiante")
