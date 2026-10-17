from collections import defaultdict
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import (
    AcademicPeriod,
    AttendanceRecord,
    Course,
    CourseAssignment,
    Enrollment,
    GradeRecord,
    Section,
)
from app.models.student import Student
from app.models.user import User
from app.services.academic_access import record_scope, student_scope
from app.services.performance_forecast import load_model, observed_history, project

router = APIRouter()


@router.get("/forecast")
def forecast(
    period_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles("coordinator"))],
    student_id: UUID | None = None,
    section_id: UUID | None = None,
    course_id: UUID | None = None,
    horizon: Literal["exam", "bimester"] = "exam",
    as_of: date | None = None,
    through_bimester: Annotated[int | None, Query(ge=1, le=100)] = None,
):
    today = datetime.now(ZoneInfo("America/Lima")).date()
    as_of = as_of or today
    if as_of > today:
        raise HTTPException(422, "La fecha de corte no puede estar en el futuro")
    if not student_id and not section_id:
        raise HTTPException(422, "Selecciona un alumno o un aula")
    if horizon == "bimester" and through_bimester is None:
        raise HTTPException(422, "Indica el último bimestre completado")
    period = db.get(AcademicPeriod, period_id)
    if period is None:
        raise HTTPException(404, "Periodo no encontrado")
    if as_of < period.starts_on:
        raise HTTPException(422, "La fecha de corte precede al periodo seleccionado")
    cutoff = min(as_of, period.ends_on)
    pupils_query = select(Student).where(Student.status == "ACTIVE", student_scope(user))
    if section_id:
        if db.get(Section, section_id) is None:
            raise HTTPException(404, "Aula no encontrada")
        pupils_query = pupils_query.where(Student.section_id == section_id)
    if student_id:
        pupils_query = pupils_query.where(Student.id == student_id)
    pupils = db.scalars(pupils_query.order_by(Student.last_name, Student.first_name)).all()
    if student_id and not pupils:
        raise HTTPException(404, "Alumno no disponible en el ámbito seleccionado")
    ids = [s.id for s in pupils]
    periods = db.scalars(
        select(AcademicPeriod).where(AcademicPeriod.starts_on <= period.starts_on)
    ).all()
    period_ids = [p.id for p in periods]
    grade_query = select(GradeRecord).where(
        GradeRecord.student_id.in_(ids),
        GradeRecord.period_id.in_(period_ids),
        record_scope(GradeRecord, user),
    )
    attendance_query = select(AttendanceRecord).where(
        AttendanceRecord.student_id.in_(ids),
        AttendanceRecord.period_id.in_(period_ids),
        AttendanceRecord.attendance_date <= cutoff,
        record_scope(AttendanceRecord, user),
    )
    if course_id:
        grade_query = grade_query.where(GradeRecord.course_id == course_id)
        attendance_query = attendance_query.where(AttendanceRecord.course_id == course_id)
    grades, attendance = defaultdict(list), defaultdict(list)
    for row in db.scalars(grade_query):
        grades[(row.student_id, row.course_id)].append(row)
    for row in db.scalars(attendance_query):
        attendance[(row.student_id, row.course_id)].append(row)
    pairs = set(grades)
    enrollments = select(Enrollment).where(
        Enrollment.student_id.in_(ids),
        Enrollment.period_id == period_id,
        Enrollment.status == "ACTIVE",
        record_scope(Enrollment, user),
    )
    for row in db.scalars(enrollments):
        if not course_id or row.course_id == course_id:
            pairs.add((row.student_id, row.course_id))
    assignments = db.scalars(
        select(CourseAssignment).where(
            CourseAssignment.section_id.in_([s.section_id for s in pupils])
        )
    )
    for assignment in assignments:
        if user.role.code == "teacher" and assignment.teacher_id != user.id:
            continue
        if course_id and assignment.course_id != course_id:
            continue
        for pupil in pupils:
            if pupil.section_id == assignment.section_id and pupil.grade_id == assignment.grade_id:
                pairs.add((pupil.id, assignment.course_id))
    pupil_map = {p.id: p for p in pupils}
    courses = {
        c.id: c.name for c in db.scalars(select(Course).where(Course.id.in_([c for _, c in pairs])))
    }
    try:
        model = load_model()
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        raise HTTPException(503, "Modelo de proyección no disponible") from exc
    rows = []
    for pupil_id, cid in sorted(
        pairs,
        key=lambda pair: (
            pupil_map[pair[0]].last_name,
            pupil_map[pair[0]].first_name,
            courses.get(pair[1], ""),
            str(pair[0]),
            str(pair[1]),
        ),
    ):
        history, excluded = observed_history(
            grades[(pupil_id, cid)], periods, horizon, cutoff, through_bimester, period_id
        )
        # Attendance has no bimester identity. For bimester projections only use prior
        # closed periods, rather than including attendance from an unobserved bimester.
        records = attendance[(pupil_id, cid)]
        if horizon == "bimester":
            closed = {p.id for p in periods if p.ends_on <= cutoff and p.id != period_id}
            records = [r for r in records if r.period_id in closed]
        pupil = pupil_map[pupil_id]
        prediction = project(history, records, horizon, model)
        if horizon == "bimester" and not any(
            h["period_id"] == str(period_id) and h["bimester"] == through_bimester for h in history
        ):
            prediction = project([], [], horizon, model)
            prediction["recommendations"] = [
                "Faltan notas del último bimestre indicado en el periodo seleccionado. "
                "Completa el historial antes de proyectar el siguiente."
            ]
        rows.append(
            {
                "student_id": str(pupil_id),
                "student_name": f"{pupil.last_name}, {pupil.first_name}",
                "course_id": str(cid),
                "course_name": courses[cid],
                "history": history,
                "excluded_records": excluded,
                "attendance_count": len(records),
                "synthetic_records": sum(r.data_origin == "synthetic" for r in grades[(pupil_id, cid)]),
                "prediction": prediction,
            }
        )
    available = [r["prediction"]["score"] for r in rows if r["prediction"]["score"] is not None]
    return {
        "mode": "experimental",
        "training_source": "synthetic",
        "horizon": horizon,
        "as_of": cutoff,
        "through_bimester": through_bimester,
        "generated_at": datetime.now(ZoneInfo("America/Lima")),
        "model_version": model["version"],
        "validation": model["horizons"][horizon]["metrics"],
        "training_split": model["horizons"][horizon]["split"],
        "summary": {
            "students": len(pupils),
            "course_cases": len(rows),
            "predicted": len(available),
            "insufficient": len(rows) - len(available),
            "projected_average": round(sum(available) / len(available), 2) if available else None,
        },
        "warning": "Modelo entrenado con datos ficticios. Proyecciones orientativas sin "
        "validación institucional; no son notas oficiales ni generan alertas.",
        "interval_note": "Rango del 90 % calibrado con validación sintética; "
        "no garantiza cobertura en alumnos reales.",
        "rows": rows,
    }
