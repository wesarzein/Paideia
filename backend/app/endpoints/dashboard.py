from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AttendanceRecord, GradeRecord
from app.models.student import Student
from app.models.user import User
from app.schemas.dashboard import DashboardSummary, RiskAlert

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher")),
    grade_id: UUID | None = None,
    section_id: UUID | None = None,
    period_id: UUID | None = None,
) -> DashboardSummary:
    students_query = select(Student)
    if grade_id: students_query = students_query.where(Student.grade_id == grade_id)
    if section_id: students_query = students_query.where(Student.section_id == section_id)
    students = db.scalars(students_query).all()
    student_ids = [student.id for student in students]
    grade_query = select(GradeRecord).where(GradeRecord.student_id.in_(student_ids)) if student_ids else select(GradeRecord).where(False)
    attendance_query = select(AttendanceRecord).where(AttendanceRecord.student_id.in_(student_ids)) if student_ids else select(AttendanceRecord).where(False)
    if period_id:
        grade_query = grade_query.where(GradeRecord.period_id == period_id)
        attendance_query = attendance_query.where(AttendanceRecord.period_id == period_id)
    grades = db.scalars(grade_query).all()
    attendances = db.scalars(attendance_query).all()
    total_students = len(students)
    active_students = sum(student.status == "ACTIVE" for student in students)
    average_score = sum(item.score for item in grades) / len(grades) if grades else 0.0
    attendance_rate = db.scalar(
        select(func.avg(case((AttendanceRecord.status == "PRESENT", 1.0), else_=0.0))).where(AttendanceRecord.id.in_([item.id for item in attendances]))
    ) or 0.0
    at_risk_count = sum(1 for student in students if sum(item.score for item in grades if item.student_id == student.id) / max(1, sum(item.student_id == student.id for item in grades)) < 12)
    return DashboardSummary(
        total_students=total_students,
        active_students=active_students,
        average_score=float(average_score),
        attendance_rate=float(attendance_rate) * 100,
        at_risk_count=at_risk_count,
    )


@router.get("/risk-alerts", response_model=list[RiskAlert])
def risk_alerts(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher")),
) -> list[RiskAlert]:
    students = db.scalars(select(Student)).all()
    alerts: list[RiskAlert] = []
    for student in students:
        scores = db.scalars(select(GradeRecord.score).where(GradeRecord.student_id == student.id)).all()
        attendances = db.scalars(select(AttendanceRecord.status).where(AttendanceRecord.student_id == student.id)).all()
        avg_score = sum(scores) / len(scores) if scores else 0
        attendance_rate = (sum(1 for status in attendances if status == "PRESENT") / len(attendances)) * 100 if attendances else 0
        if avg_score < 12 or attendance_rate < 70:
            alerts.append(
                RiskAlert(
                    student_id=str(student.id),
                    student_name=f"{student.last_name}, {student.first_name}",
                    average_score=avg_score,
                    attendance_rate=attendance_rate,
                    risk_level="ALTO" if avg_score < 10 else "MEDIO",
                )
            )
    return alerts
