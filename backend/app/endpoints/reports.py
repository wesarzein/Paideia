from io import BytesIO
from uuid import UUID
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import case, extract, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.academic_rules import literal_grade
from app.core.database import get_db
from app.models.academic import AttendanceRecord, Course, CourseAssignment, Grade, GradeRecord, Section
from app.models.follow_up import FollowUp
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
    course_id: UUID | None = None,
    month: int | None = None,
) -> list[StudentReport]:
    if month is not None and not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month debe estar entre 1 y 12")
    reports: list[StudentReport] = []
    students_query = select(Student).where(Student.status == "ACTIVE")
    if _user.role.code == "teacher":
        students_query = students_query.join(
            CourseAssignment,
            (CourseAssignment.grade_id == Student.grade_id)
            & (CourseAssignment.section_id == Student.section_id),
        ).where(CourseAssignment.teacher_id == _user.id).distinct()
    if grade_id: students_query = students_query.where(Student.grade_id == grade_id)
    if section_id: students_query = students_query.where(Student.section_id == section_id)
    for student in db.scalars(students_query).all():
        grade_query = select(GradeRecord.score).where(GradeRecord.student_id == student.id)
        attendance_query = select(AttendanceRecord.status).where(AttendanceRecord.student_id == student.id)
        if _user.role.code == "teacher":
            assigned_courses = select(CourseAssignment.course_id).where(
                CourseAssignment.grade_id == student.grade_id,
                CourseAssignment.section_id == student.section_id,
                CourseAssignment.teacher_id == _user.id,
            )
            grade_query = grade_query.where(GradeRecord.course_id.in_(assigned_courses))
            attendance_query = attendance_query.where(AttendanceRecord.course_id.in_(assigned_courses))
        if period_id:
            grade_query = grade_query.where(GradeRecord.period_id == period_id)
            attendance_query = attendance_query.where(AttendanceRecord.period_id == period_id)
        if course_id:
            grade_query = grade_query.where(GradeRecord.course_id == course_id)
            attendance_query = attendance_query.where(AttendanceRecord.course_id == course_id)
        if month is not None:
            grade_query = grade_query.where(extract("month", GradeRecord.assessment_date) == month)
            attendance_query = attendance_query.where(extract("month", AttendanceRecord.attendance_date) == month)
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
                student_code=student.student_code,
                student_name=f"{student.last_name}, {student.first_name}",
                average_score=avg_score,
                attendance_rate=attendance_rate,
                risk_level=risk_level,
            )
        )
    return reports


@router.get("/students/{student_id}")
def individual_report(
    student_id: UUID,
    period_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
) -> dict:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    grade = db.get(Grade, student.grade_id) if student.grade_id else None
    section = db.get(Section, student.section_id) if student.section_id else None
    assigned_courses = None
    if user.role.code == "teacher":
        assigned_courses = select(CourseAssignment.course_id).where(
            CourseAssignment.grade_id == student.grade_id,
            CourseAssignment.section_id == student.section_id,
            CourseAssignment.teacher_id == user.id,
        )
        if db.scalar(select(CourseAssignment.id).where(CourseAssignment.grade_id == student.grade_id, CourseAssignment.section_id == student.section_id, CourseAssignment.teacher_id == user.id)) is None:
            raise HTTPException(status_code=403, detail="No tienes acceso al seguimiento de este estudiante")
    grades_query = select(GradeRecord, Course.name).join(Course, Course.id == GradeRecord.course_id).where(GradeRecord.student_id == student_id)
    attendance_query = select(AttendanceRecord, Course.name).join(Course, Course.id == AttendanceRecord.course_id).where(AttendanceRecord.student_id == student_id)
    if assigned_courses is not None:
        grades_query = grades_query.where(GradeRecord.course_id.in_(assigned_courses))
        attendance_query = attendance_query.where(AttendanceRecord.course_id.in_(assigned_courses))
    if period_id:
        grades_query = grades_query.where(GradeRecord.period_id == period_id)
        attendance_query = attendance_query.where(AttendanceRecord.period_id == period_id)
    grade_rows = db.execute(grades_query.order_by(GradeRecord.assessment_date, GradeRecord.created_at)).all()
    attendance_rows = db.execute(attendance_query.order_by(AttendanceRecord.attendance_date)).all()
    follow_ups = db.scalars(select(FollowUp).where(FollowUp.student_id == student_id).order_by(FollowUp.created_at.desc())).all()
    return {
        "student": {"id": str(student.id), "student_code": student.student_code, "name": f"{student.last_name}, {student.first_name}", "grade": grade.name if grade else None, "level": grade.level if grade else None, "section": section.name if section else None},
        "grades": [{"course": course_name, "evaluation": record.evaluation_name, "component": record.evaluation_type, "date": record.assessment_date.isoformat(), "score": record.score, "literal": literal_grade(record.score), "note": record.qualitative_note} for record, course_name in grade_rows],
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
    user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
) -> StreamingResponse:
    if month is not None and not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month debe estar entre 1 y 12")
    rows = student_reports(db=db, _user=user, grade_id=grade_id, section_id=section_id, period_id=period_id, course_id=course_id, month=month)
    frame = pd.DataFrame([row.model_dump(mode="json") for row in rows])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="Reporte grupal", index=False)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=paideia-reporte-grupal.xlsx"})
