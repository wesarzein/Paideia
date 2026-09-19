from uuid import UUID
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AttendanceRecord, GradeRecord
from app.models.student import Student
from app.models.user import User
from app.schemas.reports import ReportSummary, StudentReport

router = APIRouter()


@router.get("/summary", response_model=ReportSummary)
def reports_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher")),
) -> ReportSummary:
    total_students = db.scalar(select(func.count()).select_from(Student)) or 0
    average_score = db.scalar(select(func.avg(GradeRecord.score))) or 0.0
    attendance_rate = db.scalar(
        select(func.avg(case((AttendanceRecord.status == "PRESENT", 1.0), else_=0.0)))
    ) or 0.0
    alerts = 0
    for student in db.scalars(select(Student)).all():
        scores = db.scalars(select(GradeRecord.score).where(GradeRecord.student_id == student.id)).all()
        attendances = db.scalars(select(AttendanceRecord.status).where(AttendanceRecord.student_id == student.id)).all()
        avg_score = sum(scores) / len(scores) if scores else 0
        rate = (sum(1 for status in attendances if status == "PRESENT") / len(attendances)) * 100 if attendances else 0
        if avg_score < 12 or rate < 70:
            alerts += 1
    return ReportSummary(
        total_students=total_students,
        average_score=float(average_score),
        attendance_rate=float(attendance_rate) * 100,
        at_risk_count=alerts,
    )


@router.get("/students", response_model=list[StudentReport])
def student_reports(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher")),
    grade_id: UUID | None = None,
    section_id: UUID | None = None,
    period_id: UUID | None = None,
) -> list[StudentReport]:
    reports: list[StudentReport] = []
    students_query = select(Student)
    if grade_id: students_query = students_query.where(Student.grade_id == grade_id)
    if section_id: students_query = students_query.where(Student.section_id == section_id)
    for student in db.scalars(students_query).all():
        grade_query = select(GradeRecord.score).where(GradeRecord.student_id == student.id)
        attendance_query = select(AttendanceRecord.status).where(AttendanceRecord.student_id == student.id)
        if period_id:
            grade_query = grade_query.where(GradeRecord.period_id == period_id)
            attendance_query = attendance_query.where(AttendanceRecord.period_id == period_id)
        scores = db.scalars(grade_query).all()
        attendances = db.scalars(attendance_query).all()
        avg_score = sum(scores) / len(scores) if scores else 0
        attendance_rate = (sum(1 for status in attendances if status == "PRESENT") / len(attendances)) * 100 if attendances else 0
        if avg_score < 10:
            risk_level = "ALTO"
        elif avg_score < 12 or attendance_rate < 70:
            risk_level = "MEDIO"
        else:
            risk_level = "BAJO"
        reports.append(
            StudentReport(
                student_id=student.id,
                student_name=f"{student.last_name}, {student.first_name}",
                average_score=avg_score,
                attendance_rate=attendance_rate,
                risk_level=risk_level,
            )
        )
    return reports
