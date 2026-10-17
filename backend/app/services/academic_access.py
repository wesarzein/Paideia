from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import false, select, true
from sqlalchemy.orm import Session

from app.models.academic import CourseAssignment, Enrollment, GradeRecord
from app.models.student import Student
from app.models.user import User


def student_scope(user: User, course_id=None):
    """SQL predicate for student metadata, optionally limited to one teaching course."""
    role = user.role.code
    if role in {"admin", "coordinator"}:
        return true()
    if role != "teacher":
        return false()
    assignments = select(CourseAssignment.id).where(
        CourseAssignment.teacher_id == user.id,
        CourseAssignment.grade_id == Student.grade_id,
        CourseAssignment.section_id == Student.section_id,
    )
    if course_id is not None:
        assignments = assignments.where(CourseAssignment.course_id == course_id)
    return assignments.correlate_except(CourseAssignment).exists()


def record_scope(model, user: User):
    """Correlate course AND student section; a course taught elsewhere is insufficient."""
    predicate = (
        select(Student.id)
        .where(Student.id == model.student_id, student_scope(user, model.course_id))
        .correlate_except(Student)
        .exists()
    )
    return predicate & GradeRecord.superseded_by_id.is_(None) if model is GradeRecord else predicate


def ensure_student_read_access(db: Session, user: User, student: Student) -> None:
    if db.scalar(select(Student.id).where(Student.id == student.id, student_scope(user))) is None:
        raise HTTPException(status_code=403, detail="No tienes acceso a este estudiante")


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
        raise HTTPException(
            status_code=409,
            detail="No existe asignación del curso a esta sección ni matrícula activa",
        )
