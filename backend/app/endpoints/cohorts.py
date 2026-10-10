"""Manage academic labels while preserving school-code prefixes and references."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import CourseAssignment, Grade, Section
from app.models.user import AuditLog, User
from app.schemas.cohorts import (
    GradeCreate,
    GradeLabel,
    GradeResponse,
    SectionCreate,
    SectionLabel,
    SectionResponse,
)
from app.services.student_codes import student_code_prefix

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_roles("admin"))]
Reader = Annotated[User, Depends(require_roles("admin", "teacher", "coordinator", "director"))]


def lock_catalog(db: Session) -> None:
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('academic-cohorts', 0))"))


def prefix(grade: Grade, section: Section | None = None) -> str:
    try:
        return student_code_prefix(grade, section or Section(name="A"))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def duplicate(db: Session, model, name: str, identity=None, grade_id=None) -> None:
    query = select(model.id).where(func.lower(func.trim(model.name)) == name.lower())
    if identity:
        query = query.where(model.id != identity)
    if model is Section:
        query = query.where(Section.grade_id == grade_id)
    if db.scalar(query.limit(1)) is not None:
        raise HTTPException(status_code=409, detail="Ya existe una etiqueta con ese nombre")


def save(db: Session, item, user: User, action: str):
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_email=user.email, action=action, entity=item.__tablename__, details=str(item.id)
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/grades", response_model=list[GradeResponse])
def list_grades(db: Db, _user: Reader):
    query = select(Grade)
    if _user.role.code in {"teacher", "coordinator", "director"}:
        query = query.where(
            Grade.id.in_(
                select(CourseAssignment.grade_id).where(CourseAssignment.teacher_id == _user.id)
            )
        )
    return db.scalars(query.order_by(Grade.level, Grade.name, Grade.id)).all()


@router.post("/grades", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
def create_grade(payload: GradeCreate, db: Db, user: Admin):
    lock_catalog(db)
    grade = Grade(name=payload.name, level=payload.level.strip().capitalize())
    candidate = prefix(grade)
    # Distinct labels cannot allocate the same school-code prefix within a level.
    for existing in db.scalars(select(Grade).where(func.lower(Grade.level) == grade.level.lower())):
        if prefix(existing) == candidate:
            raise HTTPException(
                status_code=409, detail="Ya existe un grado con esa identidad escolar"
            )
    return save(db, grade, user, "GRADE_CREATED")


@router.patch("/grades/{grade_id}", response_model=GradeResponse)
def update_grade(grade_id: UUID, payload: GradeLabel, db: Db, user: Admin):
    lock_catalog(db)
    grade = db.get(Grade, grade_id, with_for_update=True)
    if grade is None:
        raise HTTPException(status_code=404, detail="Grado no encontrado")
    proposed = Grade(name=payload.name, level=grade.level)
    if prefix(proposed) != prefix(grade):
        raise HTTPException(
            status_code=409, detail="La edición debe conservar el número y nivel del grado"
        )
    grade.name = payload.name
    return save(db, grade, user, "GRADE_LABEL_UPDATED")


@router.get("/sections", response_model=list[SectionResponse])
def list_sections(db: Db, _user: Reader):
    query = select(Section)
    if _user.role.code in {"teacher", "coordinator", "director"}:
        query = query.where(
            Section.id.in_(
                select(CourseAssignment.section_id).where(CourseAssignment.teacher_id == _user.id)
            )
        )
    return db.scalars(query.order_by(Section.grade_id, Section.name, Section.id)).all()


@router.post("/sections", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
def create_section(payload: SectionCreate, db: Db, user: Admin):
    lock_catalog(db)
    grade = db.get(Grade, payload.grade_id)
    if grade is None:
        raise HTTPException(status_code=404, detail="Grado no encontrado")
    if not grade.is_active:
        raise HTTPException(status_code=409, detail="Selecciona un grado activo")
    section = Section(grade_id=grade.id, name=payload.name.strip().upper())
    prefix(grade, section)
    duplicate(db, Section, section.name, grade_id=grade.id)
    return save(db, section, user, "SECTION_CREATED")


@router.patch("/sections/{section_id}", response_model=SectionResponse)
def update_section(
    section_id: UUID,
    payload: SectionLabel,
    db: Db,
    user: Admin,
):
    lock_catalog(db)
    section = db.get(Section, section_id, with_for_update=True)
    if section is None:
        raise HTTPException(status_code=404, detail="Sección no encontrada")
    grade = db.get(Grade, section.grade_id)
    proposed = Section(name=payload.name.strip().upper())
    if prefix(grade, proposed) != prefix(grade, section):
        raise HTTPException(
            status_code=409,
            detail="La edición debe conservar la letra de sección del código escolar",
        )
    duplicate(db, Section, proposed.name, identity=section.id, grade_id=grade.id)
    section.name = proposed.name
    return save(db, section, user, "SECTION_LABEL_UPDATED")
