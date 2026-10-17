from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AttendanceRecord, GradeRecord
from app.models.student import Student
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.services.academic_access import record_scope, student_scope
from app.services.academic_metrics import academic_metrics
from app.services.grade_provenance import month_expression

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator")),
    grade_id: UUID | None = None,
    section_id: UUID | None = None,
    course_id: UUID | None = None,
    period_id: UUID | None = None,
    month: int | None = None,
) -> DashboardSummary:
    if month is not None and not 1 <= month <= 12:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="month debe estar entre 1 y 12")
    students_query = select(Student).where(Student.status == "ACTIVE", student_scope(user, course_id))
    if grade_id: students_query = students_query.where(Student.grade_id == grade_id)
    if section_id: students_query = students_query.where(Student.section_id == section_id)
    students = db.scalars(students_query).all()
    student_ids = [student.id for student in students]
    grade_query = select(GradeRecord).where(GradeRecord.student_id.in_(student_ids)) if student_ids else select(GradeRecord).where(False)
    attendance_query = select(AttendanceRecord).where(AttendanceRecord.student_id.in_(student_ids)) if student_ids else select(AttendanceRecord).where(False)
    grade_query = grade_query.where(record_scope(GradeRecord, user))
    attendance_query = attendance_query.where(record_scope(AttendanceRecord, user))
    if period_id:
        grade_query = grade_query.where(GradeRecord.period_id == period_id)
        attendance_query = attendance_query.where(AttendanceRecord.period_id == period_id)
    if course_id:
        grade_query = grade_query.where(GradeRecord.course_id == course_id)
        attendance_query = attendance_query.where(AttendanceRecord.course_id == course_id)
    if month is not None:
        grade_query = grade_query.where(month_expression() == month)
        attendance_query = attendance_query.where(extract("month", AttendanceRecord.attendance_date) == month)
    grades = db.scalars(grade_query).all()
    attendances = db.scalars(attendance_query).all()
    total_students = len(students)
    active_students = sum(student.status == "ACTIVE" for student in students)
    metrics = academic_metrics(grades, attendances)
    alerts = sum(academic_metrics(
        [record for record in grades if record.student_id == student.id],
        [record for record in attendances if record.student_id == student.id],
    ).risk_level in {"ALTO", "MEDIO"} for student in students)
    return DashboardSummary(
        total_students=total_students,
        active_students=active_students,
        average_score=metrics.average_score,
        attendance_rate=metrics.attendance_rate,
        at_risk_count=alerts,
    )


@router.get("/risk-alerts")
def risk_alerts(
    _user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> dict[str, str]:
    raise HTTPException(status_code=501, detail="El módulo de IA aún no está habilitado")
