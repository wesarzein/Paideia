import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AttendanceRecord, GradeRecord
from app.models.user import User

router = APIRouter()


@router.get("")
def calculate_kpis(db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "teacher", "coordinator", "director"))) -> dict:
    grades = pd.DataFrame([{ "student_id": str(row.student_id), "score": row.score } for row in db.scalars(select(GradeRecord)).all()])
    attendance = pd.DataFrame([{ "student_id": str(row.student_id), "present": row.status.upper() == "PRESENT" } for row in db.scalars(select(AttendanceRecord)).all()])
    return {"average_score": round(float(grades["score"].mean()), 2) if not grades.empty else 0, "attendance_rate": round(float(attendance["present"].mean() * 100), 2) if not attendance.empty else 0, "grades_count": len(grades), "attendance_count": len(attendance)}