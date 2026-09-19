from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AcademicPeriod, Course, Grade, Section
from app.models.student import Student
from app.models.user import User

router = APIRouter()


@router.get("/catalog")
def academic_catalog(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher")),
) -> dict[str, list[dict[str, str]]]:
    grades = db.scalars(select(Grade).order_by(Grade.level, Grade.name)).all()
    sections = db.scalars(select(Section).order_by(Section.name)).all()
    courses = db.scalars(select(Course).order_by(Course.name)).all()
    periods = db.scalars(select(AcademicPeriod).order_by(AcademicPeriod.starts_on)).all()
    students = db.scalars(select(Student).where(Student.status == "ACTIVE").order_by(Student.last_name)).all()
    return {
        "grades": [{"id": str(item.id), "name": item.name, "level": item.level} for item in grades],
        "sections": [{"id": str(item.id), "name": item.name, "grade_id": str(item.grade_id)} for item in sections],
        "courses": [{"id": str(item.id), "name": item.name, "code": item.code} for item in courses],
        "periods": [{"id": str(item.id), "name": item.name} for item in periods],
        "students": [
            {"id": str(item.id), "name": f"{item.last_name}, {item.first_name}"}
            for item in students
        ],
    }