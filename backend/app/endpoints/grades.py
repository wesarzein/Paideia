from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.academic_rules import LITERAL_GRADE_THRESHOLDS, literal_grade
from app.core.database import get_db
from app.models.academic import (
    AcademicPeriod,
    Course,
    CourseAssessmentComponent,
    CourseAssignment,
    GradeRecord,
)
from app.models.student import Student
from app.models.user import User
from app.schemas.grades import GradeCreate, GradeResponse, GradeSummary, GradeUpdate
from app.services.academic_access import (
    ensure_student_course_access,
    ensure_student_read_access,
    record_scope,
)
from app.services.evaluation_revisions import latest_published_revision, revision_configuration

router = APIRouter()


@router.get("", response_model=list[GradeResponse])
def list_grades(student_id: UUID | None = None, course_id: UUID | None = None, period_id: UUID | None = None, grade_id: UUID | None = None, section_id: UUID | None = None, month: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "teacher", "coordinator", "director", "student", "parent"))) -> list[GradeRecord]:
    statement = select(GradeRecord).where(record_scope(GradeRecord, user))
    if grade_id or section_id:
        statement = statement.join(Student, GradeRecord.student_id == Student.id)
    if student_id: statement = statement.where(GradeRecord.student_id == student_id)
    if course_id: statement = statement.where(GradeRecord.course_id == course_id)
    if period_id: statement = statement.where(GradeRecord.period_id == period_id)
    if grade_id: statement = statement.where(Student.grade_id == grade_id)
    if section_id: statement = statement.where(Student.section_id == section_id)
    if month is not None:
        if not 1 <= month <= 12:
            raise HTTPException(status_code=422, detail="month debe estar entre 1 y 12")
        statement = statement.where(extract("month", GradeRecord.assessment_date) == month)
    return db.scalars(statement.order_by(GradeRecord.created_at.desc())).all()


@router.post("", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
def create_grade(
    payload: GradeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher")),
) -> GradeRecord:
    student = db.get(Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    if not db.get(Course, payload.course_id):
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    if not db.get(AcademicPeriod, payload.period_id):
        raise HTTPException(status_code=404, detail="Periodo no encontrado")

    if payload.component_id:
        component = db.get(CourseAssessmentComponent, payload.component_id)
        if component is None or component.course_id != payload.course_id or not component.is_active:
            raise HTTPException(status_code=422, detail="El componente no está activo para este curso")

    ensure_student_course_access(db, user, student, payload.course_id, payload.period_id)

    revision = latest_published_revision(db, payload.course_id, payload.period_id)
    if revision:
        if not all(
            value is not None
            for value in (
                payload.academic_bimester,
                payload.evaluation_block,
                payload.evaluation_criterion_key,
            )
        ):
            raise HTTPException(
                status_code=422,
                detail="Selecciona bimestre, bloque y criterio de la configuración publicada",
            )
        configuration = revision_configuration(revision)
        criterion = next(
            (
                item
                for item in configuration.criteria
                if item.key == payload.evaluation_criterion_key
            ),
            None,
        )
        if (
            criterion is None
            or not criterion.is_active
            or criterion.block != payload.evaluation_block
        ):
            raise HTTPException(
                status_code=422,
                detail="El criterio no está activo en el bloque seleccionado",
            )
        if (
            payload.component_id
            and criterion.legacy_component_id
            and str(payload.component_id) != criterion.legacy_component_id
        ):
            raise HTTPException(
                status_code=422,
                detail="El componente no corresponde al criterio publicado",
            )

    record = GradeRecord(
        student_id=payload.student_id,
        course_id=payload.course_id,
        period_id=payload.period_id,
        component_id=payload.component_id,
        academic_bimester=payload.academic_bimester,
        evaluation_block=payload.evaluation_block,
        evaluation_criterion_key=payload.evaluation_criterion_key,
        evaluation_name=payload.evaluation_name.strip(),
        evaluation_type=payload.evaluation_type.strip(),
        assessment_date=payload.assessment_date,
        score=float(payload.score),
        qualitative_note=payload.qualitative_note,
        evaluation_revision_id=revision.id if revision else None,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una nota para esta evaluación y criterio, o sus relaciones no son válidas") from error
    db.refresh(record)
    return record


@router.get("/monthly-summary")
def monthly_summary(
    grade_id: UUID,
    section_id: UUID,
    course_id: UUID,
    period_id: UUID,
    month: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
) -> dict:
    if not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month debe estar entre 1 y 12")
    if user.role.code == "teacher" and db.scalar(select(CourseAssignment.id).where(CourseAssignment.course_id == course_id, CourseAssignment.grade_id == grade_id, CourseAssignment.section_id == section_id, CourseAssignment.teacher_id == user.id)) is None:
        raise HTTPException(status_code=403, detail="No tienes asignado este curso y sección")
    rows = db.execute(
        select(
            GradeRecord.student_id,
            func.sum(GradeRecord.score * GradeRecord.assessment_weight)
            / func.nullif(func.sum(GradeRecord.assessment_weight), 0),
            func.count(GradeRecord.id),
        )
        .join(Student, Student.id == GradeRecord.student_id)
        .where(
            Student.grade_id == grade_id,
            Student.section_id == section_id,
            GradeRecord.course_id == course_id,
            GradeRecord.period_id == period_id,
            extract("month", GradeRecord.assessment_date) == month,
        )
        .group_by(GradeRecord.student_id)
    ).all()
    return {
        "thresholds": [{"greater_than": threshold, "grade": label} for threshold, label in LITERAL_GRADE_THRESHOLDS],
        "students": [
            {"student_id": str(student_id), "average": round(float(average or 0), 2), "literal": literal_grade(float(average or 0)), "components_recorded": count}
            for student_id, average, count in rows
        ],
    }


@router.patch("/{grade_id}", response_model=GradeResponse)
def update_grade(grade_id: UUID, payload: GradeUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "teacher"))) -> GradeRecord:
    record = db.get(GradeRecord, grade_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Calificación no encontrada")
    student = db.get(Student, record.student_id)
    ensure_student_course_access(db, user, student, record.course_id, record.period_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in {"evaluation_name", "evaluation_type"} and isinstance(value, str):
            value = value.strip()
        setattr(record, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="La modificación entra en conflicto con una nota existente o una relación inválida") from error
    db.refresh(record)
    return record


@router.delete("/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade(grade_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "teacher"))) -> None:
    record = db.get(GradeRecord, grade_id)
    if record is None: raise HTTPException(status_code=404, detail="Calificación no encontrada")
    student = db.get(Student, record.student_id)
    ensure_student_course_access(db, user, student, record.course_id, record.period_id)
    db.delete(record); db.commit()


@router.get("/summary/{student_id}", response_model=GradeSummary)
def summary_by_student(
    student_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator", "director", "student", "parent")),
) -> GradeSummary:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    ensure_student_read_access(db, user, student)
    results = db.execute(
        select(GradeRecord.score).where(
            GradeRecord.student_id == student_id, record_scope(GradeRecord, user)
        )
    ).scalars().all()
    if not results:
        return GradeSummary(student_id=student_id, average=0.0, count=0)
    average = sum(results) / len(results)
    return GradeSummary(student_id=student_id, average=average, count=len(results))
