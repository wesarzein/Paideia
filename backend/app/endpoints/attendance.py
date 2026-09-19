from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AcademicPeriod, AttendanceRecord, Course
from app.models.student import Student
from app.models.user import User
from app.schemas.attendance import AttendanceCreate, AttendanceResponse

router = APIRouter()


@router.get("", response_model=list[AttendanceResponse])
def list_attendance(db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "teacher"))) -> list[AttendanceRecord]:
    return db.scalars(select(AttendanceRecord).order_by(AttendanceRecord.attendance_date.desc())).all()


@router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def create_attendance(
    payload: AttendanceCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher")),
) -> AttendanceRecord:
    if not db.get(Student, payload.student_id):
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    if not db.get(Course, payload.course_id):
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    if not db.get(AcademicPeriod, payload.period_id):
        raise HTTPException(status_code=404, detail="Periodo no encontrado")

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
