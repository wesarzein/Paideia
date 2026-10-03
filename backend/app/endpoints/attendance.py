from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AcademicPeriod, AttendanceRecord, Course, CourseAssignment
from app.models.student import Student
from app.models.user import User
from app.schemas.attendance import AttendanceCreate, AttendanceResponse
from app.services.academic_access import ensure_student_course_access

router = APIRouter()


@router.get("", response_model=list[AttendanceResponse])
def list_attendance(grade_id: UUID | None = None, section_id: UUID | None = None, course_id: UUID | None = None, period_id: UUID | None = None, attendance_date: date | None = None, month: int | None = None, student_id: UUID | None = None, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "teacher", "coordinator", "director", "student", "parent"))) -> list[AttendanceRecord]:
    statement = select(AttendanceRecord)
    if grade_id or section_id or student_id or _user.role.code in {"teacher", "student", "parent"}:
        statement = statement.join(Student, AttendanceRecord.student_id == Student.id)
    if _user.role.code == "teacher":
        statement = statement.join(CourseAssignment, (CourseAssignment.course_id == AttendanceRecord.course_id) & (CourseAssignment.section_id == Student.section_id)).where(CourseAssignment.teacher_id == _user.id)
    elif _user.role.code == "student":
        statement = statement.where(Student.student_user_id == _user.id)
    elif _user.role.code == "parent":
        statement = statement.where(Student.parent_user_id == _user.id)
    if student_id:
        statement = statement.where(AttendanceRecord.student_id == student_id)
    if grade_id: statement = statement.where(Student.grade_id == grade_id)
    if section_id: statement = statement.where(Student.section_id == section_id)
    if course_id: statement = statement.where(AttendanceRecord.course_id == course_id)
    if period_id: statement = statement.where(AttendanceRecord.period_id == period_id)
    if attendance_date: statement = statement.where(AttendanceRecord.attendance_date == attendance_date)
    if month is not None:
        if not 1 <= month <= 12: raise HTTPException(status_code=422, detail="month debe estar entre 1 y 12")
        statement = statement.where(extract("month", AttendanceRecord.attendance_date) == month)
    return db.scalars(statement.order_by(AttendanceRecord.attendance_date.desc())).all()


@router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def create_attendance(
    payload: AttendanceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher")),
) -> AttendanceRecord:
    if not db.get(Student, payload.student_id):
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    if not db.get(Course, payload.course_id):
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    if not db.get(AcademicPeriod, payload.period_id):
        raise HTTPException(status_code=404, detail="Periodo no encontrado")

    ensure_student_course_access(db, user, db.get(Student, payload.student_id), payload.course_id, payload.period_id)

    attendance = db.scalar(select(AttendanceRecord).where(AttendanceRecord.student_id == payload.student_id, AttendanceRecord.course_id == payload.course_id, AttendanceRecord.attendance_date == payload.attendance_date))
    if attendance is not None:
        attendance.period_id = payload.period_id
        attendance.status = payload.status.upper()
        attendance.remarks = payload.remarks
        db.commit()
        db.refresh(attendance)
        return attendance

    attendance = AttendanceRecord(
        student_id=payload.student_id,
        course_id=payload.course_id,
        period_id=payload.period_id,
        attendance_date=payload.attendance_date,
        status=payload.status.upper(),
        remarks=payload.remarks,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance
