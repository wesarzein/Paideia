"""Academic calendars are edited without deleting identities or invalidating records."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AcademicPeriod, AttendanceRecord, GradeRecord
from app.models.user import AuditLog, User
from app.schemas.periods import PeriodCreate, PeriodResponse, PeriodUpdate

router = APIRouter()


def validate_name(db: Session, name: str, period_id: UUID | None = None) -> None:
    if db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": "academic_period:" + name.lower()},
        )
    query = select(AcademicPeriod.id).where(
        func.lower(func.trim(AcademicPeriod.name)) == name.lower()
    )
    if period_id:
        query = query.where(AcademicPeriod.id != period_id)
    if db.scalar(query.limit(1)) is not None:
        raise HTTPException(status_code=409, detail="Ya existe un periodo con ese nombre")


@router.get("", response_model=list[PeriodResponse])
def list_periods(
    db: Session = Depends(get_db),
    _user: User = Depends(
        require_roles("admin", "teacher", "coordinator")
    ),
):
    return db.scalars(
        select(AcademicPeriod).order_by(
            AcademicPeriod.starts_on, AcademicPeriod.name, AcademicPeriod.id
        )
    ).all()


@router.post("", response_model=PeriodResponse, status_code=status.HTTP_201_CREATED)
def create_period(
    payload: PeriodCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    validate_name(db, payload.name)
    period = AcademicPeriod(**payload.model_dump())
    db.add(period)
    db.flush()
    db.add(
        AuditLog(
            actor_email=user.email,
            action="PERIOD_CREATED",
            entity="academic_periods",
            details=str(period.id),
        )
    )
    db.commit()
    db.refresh(period)
    return period


@router.patch("/{period_id}", response_model=PeriodResponse)
def update_period(
    period_id: UUID,
    payload: PeriodUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    period = db.get(AcademicPeriod, period_id, with_for_update=True)
    if period is None:
        raise HTTPException(status_code=404, detail="Periodo no encontrado")
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Los campos del periodo no admiten null")
    start = changes.get("starts_on", period.starts_on)
    end = changes.get("ends_on", period.ends_on)
    if start > end:
        raise HTTPException(status_code=422, detail="El inicio no puede ser posterior al fin")
    if (start, end) != (period.starts_on, period.ends_on):
        for model, date_field in (
            (GradeRecord, GradeRecord.assessment_date),
            (AttendanceRecord, AttendanceRecord.attendance_date),
        ):
            if (
                db.scalar(
                    select(model.id)
                    .where(model.period_id == period.id, or_(date_field < start, date_field > end))
                    .limit(1)
                )
                is not None
            ):
                raise HTTPException(
                    status_code=422, detail="Las fechas excluirían notas o asistencias registradas"
                )
    if "name" in changes:
        validate_name(db, changes["name"], period.id)
    for field, value in changes.items():
        setattr(period, field, value)
    if changes:
        db.add(
            AuditLog(
                actor_email=user.email,
                action="PERIOD_UPDATED",
                entity="academic_periods",
                details=str(period.id),
            )
        )
    db.commit()
    db.refresh(period)
    return period
