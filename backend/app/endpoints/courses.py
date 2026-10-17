from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import (
    AcademicPeriod,
    Course,
    CourseAssessmentComponent,
    CourseAssignment,
    EvaluationConfigurationRevision,
    Section,
)
from app.models.user import User
from app.schemas.courses import (
    AssessmentComponentCreate,
    AssessmentComponentResponse,
    AssessmentComponentUpdate,
    CourseAssignmentCreate,
    CourseAssignmentResponse,
    CourseCreate,
    CourseResponse,
    CourseUpdate,
    EvaluationPreviewRequest,
    EvaluationRestoreRequest,
    EvaluationRevisionWrite,
)
from app.services.course_catalog import canonical_course_name, unique_course_code
from app.services.evaluation_configuration import from_document, institutional_template, preview
from app.services.evaluation_revisions import (
    StaleEvaluationRevision,
    create_revision,
    latest_published_revision,
    latest_revision,
    revision_payload,
)

router = APIRouter()


def _ensure_course_access(db: Session, user: User, course_id: UUID) -> None:
    if user.role.code == "teacher" and db.scalar(select(CourseAssignment.id).where(CourseAssignment.course_id == course_id, CourseAssignment.teacher_id == user.id)) is None:
        raise HTTPException(status_code=403, detail="No tienes este curso asignado")


def _evaluation_scope(db: Session, user: User, course_id: UUID, period_id: UUID) -> None:
    if db.get(Course, course_id) is None or db.get(AcademicPeriod, period_id) is None:
        raise HTTPException(status_code=404, detail="Curso o periodo no encontrado")
    _ensure_course_access(db, user, course_id)


def _configuration_from_payload(course_id: UUID, document: dict):
    try:
        configuration = from_document(document)
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=422, detail="Documento de evaluación inválido") from error
    if configuration.course_id != str(course_id):
        raise HTTPException(status_code=422, detail="La configuración pertenece a otro curso")
    return configuration


def _store_evaluation_revision(
    db: Session,
    user: User,
    configuration,
    expected_version: int,
    reason: str,
    state: str,
) -> dict:
    _evaluation_scope(db, user, UUID(configuration.course_id), UUID(configuration.period_id))
    try:
        revision = create_revision(
            db, configuration, user.id, reason, expected_version, state
        )
        db.commit()
        db.refresh(revision)
    except StaleEvaluationRevision as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Otra edición se guardó primero; recarga la versión antes de continuar",
        ) from error
    return revision_payload(revision)


def _default_evaluation_payload(course_id: UUID, period_id: UUID) -> dict:
    configuration = institutional_template(str(course_id), str(period_id))
    return {
        "id": None,
        "course_id": str(course_id),
        "period_id": str(period_id),
        "version": 0,
        "state": "default",
        "previous_revision_id": None,
        "configuration": configuration.document(),
        "content_hash": configuration.fingerprint(),
        "reason": "Plantilla institucional predeterminada",
        "created_by_id": None,
        "created_at": None,
    }


@router.get("/{course_id}/evaluation-template")
def get_evaluation_template(
    course_id: UUID,
    period_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> dict:
    _evaluation_scope(db, user, course_id, period_id)
    return institutional_template(str(course_id), str(period_id)).document()


@router.post("/{course_id}/evaluation-preview")
def preview_evaluation_configuration(
    course_id: UUID,
    payload: EvaluationPreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> dict:
    config = _configuration_from_payload(course_id, payload.configuration)
    _evaluation_scope(db, user, course_id, UUID(config.period_id))
    try:
        return preview(config, payload.scores)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{course_id}/evaluation-configurations/current")
def get_current_evaluation_configuration(
    course_id: UUID,
    period_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> dict:
    _evaluation_scope(db, user, course_id, period_id)
    revision = latest_revision(db, course_id, period_id)
    if revision:
        return revision_payload(revision)
    return _default_evaluation_payload(course_id, period_id)


@router.get("/{course_id}/evaluation-configurations/active")
def get_active_evaluation_configuration(
    course_id: UUID,
    period_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> dict:
    """Return only a published revision; drafts never affect grade capture."""
    _evaluation_scope(db, user, course_id, period_id)
    revision = latest_published_revision(db, course_id, period_id)
    return revision_payload(revision) if revision else _default_evaluation_payload(
        course_id, period_id
    )


@router.get("/{course_id}/evaluation-configurations/versions")
def list_evaluation_configuration_versions(
    course_id: UUID,
    period_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> list[dict]:
    _evaluation_scope(db, user, course_id, period_id)
    revisions = db.scalars(
        select(EvaluationConfigurationRevision)
        .where(
            EvaluationConfigurationRevision.course_id == course_id,
            EvaluationConfigurationRevision.period_id == period_id,
        )
        .order_by(EvaluationConfigurationRevision.version.desc())
    ).all()
    return [revision_payload(revision) for revision in revisions]


@router.post("/{course_id}/evaluation-configurations/drafts", status_code=status.HTTP_201_CREATED)
def save_evaluation_configuration_draft(
    course_id: UUID,
    payload: EvaluationRevisionWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("teacher")),
) -> dict:
    configuration = _configuration_from_payload(course_id, payload.configuration)
    return _store_evaluation_revision(
        db, user, configuration, payload.expected_version, payload.reason, "draft"
    )


@router.post("/{course_id}/evaluation-configurations/publish", status_code=status.HTTP_201_CREATED)
def publish_evaluation_configuration(
    course_id: UUID,
    payload: EvaluationRevisionWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("teacher")),
) -> dict:
    configuration = _configuration_from_payload(course_id, payload.configuration)
    return _store_evaluation_revision(
        db, user, configuration, payload.expected_version, payload.reason, "published"
    )


@router.post(
    "/{course_id}/evaluation-configurations/restore-institutional",
    status_code=status.HTTP_201_CREATED,
)
def restore_institutional_evaluation_configuration(
    course_id: UUID,
    payload: EvaluationRestoreRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("teacher")),
) -> dict:
    configuration = institutional_template(str(course_id), str(payload.period_id))
    return _store_evaluation_revision(
        db, user, configuration, payload.expected_version, payload.reason, "published"
    )


@router.get("/{course_id}/assignments", response_model=list[CourseAssignmentResponse])
def list_course_assignments(course_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "teacher", "coordinator"))) -> list[CourseAssignment]:
    if db.get(Course, course_id) is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    statement = select(CourseAssignment).where(CourseAssignment.course_id == course_id)
    if user.role.code == "teacher": statement = statement.where(CourseAssignment.teacher_id == user.id)
    return db.scalars(statement).all()


@router.post("/{course_id}/assignments", response_model=CourseAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_course(course_id: UUID, payload: CourseAssignmentCreate, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin"))) -> CourseAssignment:
    if not payload.teacher_id:
        raise HTTPException(status_code=422, detail="Selecciona la cuenta del docente para la asignación")
    course = db.get(Course, course_id)
    section = db.get(Section, payload.section_id)
    if course is None or section is None:
        raise HTTPException(status_code=404, detail="Curso o sección no encontrado")
    if payload.teacher_id:
        teacher = db.get(User, payload.teacher_id)
        if teacher is None or teacher.role.code != "teacher":
            raise HTTPException(status_code=422, detail="La asignación debe apuntar a un usuario docente")
    existing = db.scalar(select(CourseAssignment).where(CourseAssignment.course_id == course_id, CourseAssignment.section_id == section.id))
    if existing:
        existing.teacher_id = payload.teacher_id
        existing.teacher_name = payload.teacher_name or existing.teacher_name
        db.commit()
        db.refresh(existing)
        return existing
    assignment = CourseAssignment(course_id=course_id, grade_id=section.grade_id, section_id=section.id, teacher_id=payload.teacher_id, teacher_name=payload.teacher_name)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/{course_id}/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_course_assignment(course_id: UUID, assignment_id: UUID, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin"))) -> None:
    assignment = db.get(CourseAssignment, assignment_id)
    if assignment is None or assignment.course_id != course_id:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    db.delete(assignment)
    db.commit()


@router.get("/{course_id}/assessment-components", response_model=list[AssessmentComponentResponse])
def list_assessment_components(course_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "teacher", "coordinator"))) -> list[CourseAssessmentComponent]:
    if db.get(Course, course_id) is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    _ensure_course_access(db, user, course_id)
    return db.scalars(select(CourseAssessmentComponent).where(CourseAssessmentComponent.course_id == course_id).order_by(CourseAssessmentComponent.created_at)).all()


@router.post("/{course_id}/assessment-components", response_model=AssessmentComponentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment_component(course_id: UUID, payload: AssessmentComponentCreate, db: Session = Depends(get_db), _user: User = Depends(require_roles("teacher"))) -> CourseAssessmentComponent:
    _ensure_course_access(db, _user, course_id)
    if db.get(Course, course_id) is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    component = CourseAssessmentComponent(course_id=course_id, **payload.model_dump())
    db.add(component)
    try:
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un componente con ese nombre en el curso") from error
    db.refresh(component)
    return component


@router.patch("/{course_id}/assessment-components/{component_id}", response_model=AssessmentComponentResponse)
def update_assessment_component(course_id: UUID, component_id: UUID, payload: AssessmentComponentUpdate, db: Session = Depends(get_db), _user: User = Depends(require_roles("teacher"))) -> CourseAssessmentComponent:
    _ensure_course_access(db, _user, course_id)
    component = db.get(CourseAssessmentComponent, component_id)
    if component is None or component.course_id != course_id:
        raise HTTPException(status_code=404, detail="Componente no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(component, field, value)
    db.commit()
    db.refresh(component)
    return component


@router.delete("/{course_id}/assessment-components/{component_id}", response_model=AssessmentComponentResponse)
def deactivate_assessment_component(course_id: UUID, component_id: UUID, db: Session = Depends(get_db), _user: User = Depends(require_roles("teacher"))) -> CourseAssessmentComponent:
    _ensure_course_access(db, _user, course_id)
    component = db.get(CourseAssessmentComponent, component_id)
    if component is None or component.course_id != course_id:
        raise HTTPException(status_code=404, detail="Componente no encontrado")
    component.is_active = False
    db.commit()
    db.refresh(component)
    return component


@router.get("", response_model=list[CourseResponse])
def list_courses(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> list[Course]:
    statement = select(Course).order_by(Course.name)
    if not include_inactive:
        statement = statement.where(Course.is_active.is_(True))
    elif user.role.code not in {"admin", "coordinator"}:
        raise HTTPException(status_code=403, detail="No tienes permiso para consultar cursos archivados")
    if user.role.code == "teacher":
        statement = statement.where(Course.id.in_(select(CourseAssignment.course_id).where(CourseAssignment.teacher_id == user.id))).distinct()
    return db.scalars(statement).all()


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin")),
) -> Course:
    normalized_code = payload.code.strip() if payload.code and payload.code.strip() else None
    existing = db.scalar(select(Course).where(Course.code == normalized_code)) if normalized_code else None
    if existing is not None:
        raise HTTPException(status_code=409, detail="El código del curso ya existe")

    course_name = canonical_course_name(payload.name)
    course = Course(name=course_name, code=normalized_code or unique_course_code(db, course_name))
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    _ensure_course_access(db, user, course_id)
    return course


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(course_id: UUID, payload: CourseUpdate, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin"))) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "name" and isinstance(value, str):
            value = canonical_course_name(value)
        elif field == "code" and isinstance(value, str):
            value = value.strip() or unique_course_code(db, course.name)
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: UUID, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin"))) -> None:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    course.is_active = False
    db.commit()
