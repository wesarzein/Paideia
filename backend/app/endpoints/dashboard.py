from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, extract, func, select
from sqlalchemy.orm import Session
from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AttendanceRecord, GradeRecord, CourseAssignment
from app.models.student import Student
from app.models.user import User
from app.schemas.dashboard import DashboardSummary

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
    grade_id: UUID | None = None,
    section_id: UUID | None = None,
    course_id: UUID | None = None,
    period_id: UUID | None = None,
    month: int | None = None,
) -> DashboardSummary:
    if month is not None and not 1 <= month <= 12:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="month debe estar entre 1 y 12")
    students_query = select(Student).where(Student.status == "ACTIVE")
    if user.role.code == "teacher":
        students_query = students_query.join(
            CourseAssignment,
            (CourseAssignment.grade_id == Student.grade_id)
            & (CourseAssignment.section_id == Student.section_id),
        ).where(CourseAssignment.teacher_id == user.id).distinct()
    if grade_id: students_query = students_query.where(Student.grade_id == grade_id)
    if section_id: students_query = students_query.where(Student.section_id == section_id)
    students = db.scalars(students_query).all()
    student_ids = [student.id for student in students]
    grade_query = select(GradeRecord).where(GradeRecord.student_id.in_(student_ids)) if student_ids else select(GradeRecord).where(False)
    attendance_query = select(AttendanceRecord).where(AttendanceRecord.student_id.in_(student_ids)) if student_ids else select(AttendanceRecord).where(False)
    if user.role.code == "teacher":
        course_ids = select(CourseAssignment.course_id).where(CourseAssignment.teacher_id == user.id)
        grade_query = grade_query.where(GradeRecord.course_id.in_(course_ids))
        attendance_query = attendance_query.where(AttendanceRecord.course_id.in_(course_ids))
    if period_id:
        grade_query = grade_query.where(GradeRecord.period_id == period_id)
        attendance_query = attendance_query.where(AttendanceRecord.period_id == period_id)
    if course_id:
        grade_query = grade_query.where(GradeRecord.course_id == course_id)
        attendance_query = attendance_query.where(AttendanceRecord.course_id == course_id)
    if month is not None:
        grade_query = grade_query.where(extract("month", GradeRecord.assessment_date) == month)
        attendance_query = attendance_query.where(extract("month", AttendanceRecord.attendance_date) == month)
    grades = db.scalars(grade_query).all()
    attendances = db.scalars(attendance_query).all()
    total_students = len(students)
    active_students = sum(student.status == "ACTIVE" for student in students)
    average_score = sum(item.score for item in grades) / len(grades) if grades else 0.0
    attendance_rate = db.scalar(
        select(func.avg(case((AttendanceRecord.status == "PRESENT", 1.0), else_=0.0))).where(AttendanceRecord.id.in_([item.id for item in attendances]))
    ) or 0.0
    return DashboardSummary(
        total_students=total_students,
        active_students=active_students,
        average_score=float(average_score),
        attendance_rate=float(attendance_rate) * 100,
        at_risk_count=0,
    )


@router.get("/risk-alerts")
def risk_alerts(
    _user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
) -> dict[str, str]:
    raise HTTPException(status_code=501, detail="El módulo de IA aún no está habilitado")
