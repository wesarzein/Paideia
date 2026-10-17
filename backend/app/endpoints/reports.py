from io import BytesIO
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.academic_rules import literal_grade
from app.core.database import get_db
from app.models.academic import (
    AttendanceRecord,
    Course,
    Grade,
    GradeRecord,
    Section,
)
from app.models.follow_up import FollowUp
from app.models.student import Student
from app.models.user import User
from app.schemas.reports import ReportSummary, StudentReport
from app.services.academic_access import (
    ensure_student_read_access,
    record_scope,
    student_scope,
)
from app.services.academic_metrics import academic_metrics
from app.services.grade_provenance import month_expression

router = APIRouter()


@router.get("/summary", response_model=ReportSummary)
def reports_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> ReportSummary:
    students = db.scalars(select(Student).where(Student.status == "ACTIVE", student_scope(_user))).all()
    ids = [student.id for student in students]
    grades = db.scalars(select(GradeRecord).where(GradeRecord.student_id.in_(ids), record_scope(GradeRecord, _user))).all()
    attendance = db.scalars(select(AttendanceRecord).where(AttendanceRecord.student_id.in_(ids), record_scope(AttendanceRecord, _user))).all()
    metrics = academic_metrics(grades, attendance)
    alerts = sum(academic_metrics(
        [record for record in grades if record.student_id == student.id],
        [record for record in attendance if record.student_id == student.id],
    ).risk_level in {"ALTO", "MEDIO"} for student in students)
    return ReportSummary(
        total_students=len(students),
        average_score=metrics.average_score,
        attendance_rate=metrics.attendance_rate,
        at_risk_count=alerts,
    )


@router.get("/students", response_model=list[StudentReport])
def student_reports(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher", "coordinator")),
    grade_id: UUID | None = None,
    section_id: UUID | None = None,
    period_id: UUID | None = None,
    course_id: UUID | None = None,
    month: int | None = None,
) -> list[StudentReport]:
    if month is not None and not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month debe estar entre 1 y 12")
    reports: list[StudentReport] = []
    students_query = select(Student).where(Student.status == "ACTIVE", student_scope(_user, course_id))
    if grade_id: students_query = students_query.where(Student.grade_id == grade_id)
    if section_id: students_query = students_query.where(Student.section_id == section_id)
    for student in db.scalars(students_query).all():
        grade_query = select(GradeRecord).where(GradeRecord.student_id == student.id, record_scope(GradeRecord, _user))
        attendance_query = select(AttendanceRecord).where(AttendanceRecord.student_id == student.id, record_scope(AttendanceRecord, _user))
        if period_id:
            grade_query = grade_query.where(GradeRecord.period_id == period_id)
            attendance_query = attendance_query.where(AttendanceRecord.period_id == period_id)
        if course_id:
            grade_query = grade_query.where(GradeRecord.course_id == course_id)
            attendance_query = attendance_query.where(AttendanceRecord.course_id == course_id)
        if month is not None:
            grade_query = grade_query.where(month_expression() == month)
            attendance_query = attendance_query.where(extract("month", AttendanceRecord.attendance_date) == month)
        metrics = academic_metrics(db.scalars(grade_query).all(), db.scalars(attendance_query).all())
        reports.append(
            StudentReport(
                student_id=student.id,
                student_code=student.student_code,
                student_name=f"{student.last_name}, {student.first_name}",
                average_score=metrics.average_score,
                attendance_rate=metrics.attendance_rate,
                grade_count=metrics.grade_count,
                grade_weight_sum=metrics.grade_weight_sum,
                attendance_count=metrics.attendance_count,
                risk_level=metrics.risk_level,
                synthetic_count=metrics.synthetic_count,
                recorded_count=metrics.grade_count - metrics.synthetic_count,
            )
        )
    return reports


@router.get("/students/{student_id}")
def individual_report(
    student_id: UUID,
    period_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> dict:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    ensure_student_read_access(db, user, student)
    grade = db.get(Grade, student.grade_id) if student.grade_id else None
    section = db.get(Section, student.section_id) if student.section_id else None
    grades_query = select(GradeRecord, Course.name).join(Course, Course.id == GradeRecord.course_id).where(GradeRecord.student_id == student_id, record_scope(GradeRecord, user))
    attendance_query = select(AttendanceRecord, Course.name).join(Course, Course.id == AttendanceRecord.course_id).where(AttendanceRecord.student_id == student_id, record_scope(AttendanceRecord, user))
    if period_id:
        grades_query = grades_query.where(GradeRecord.period_id == period_id)
        attendance_query = attendance_query.where(AttendanceRecord.period_id == period_id)
    grade_rows = db.execute(grades_query.order_by(GradeRecord.assessment_date, GradeRecord.created_at)).all()
    attendance_rows = db.execute(attendance_query.order_by(AttendanceRecord.attendance_date)).all()
    follow_ups = db.scalars(select(FollowUp).where(FollowUp.student_id == student_id).order_by(FollowUp.created_at.desc())).all()
    return {
        "student": {"id": str(student.id), "student_code": student.student_code, "name": f"{student.last_name}, {student.first_name}", "grade": grade.name if grade else None, "level": grade.level if grade else None, "section": section.name if section else None},
        "grades": [{"course": course_name, "evaluation": record.evaluation_name, "component": record.evaluation_type, "date": record.assessment_date.isoformat() if record.assessment_date else None, "month": record.academic_month, "data_origin": record.data_origin, "score": record.score, "literal": literal_grade(record.score), "note": record.qualitative_note} for record, course_name in grade_rows],
        "attendance": [{"course": course_name, "date": record.attendance_date.isoformat(), "status": record.status, "remarks": record.remarks} for record, course_name in attendance_rows],
        "follow_ups": [{"date": item.created_at.isoformat() if item.created_at else None, "category": item.category, "action": item.action, "status": item.status} for item in follow_ups],
    }


@router.get("/export.xlsx")
def export_group_report(
    grade_id: UUID,
    section_id: UUID | None = None,
    period_id: UUID | None = None,
    course_id: UUID | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> StreamingResponse:
    if month is not None and not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month debe estar entre 1 y 12")
    rows = student_reports(db=db, _user=user, grade_id=grade_id, section_id=section_id, period_id=period_id, course_id=course_id, month=month)
    frame = pd.DataFrame([
        row.model_dump(mode="json", exclude={"synthetic_count", "recorded_count"})
        for row in rows
    ])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="Reporte grupal", index=False)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=paideia-reporte-grupal.xlsx"})
