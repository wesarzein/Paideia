from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import Course, CourseAssessmentComponent, CourseAssignment, Section
from app.models.user import User
from app.schemas.courses import AssessmentComponentCreate, AssessmentComponentResponse, AssessmentComponentUpdate, CourseAssignmentCreate, CourseAssignmentResponse, CourseCreate, CourseResponse, CourseUpdate
from app.services.course_catalog import canonical_course_name, unique_course_code

router = APIRouter()


def _ensure_course_access(db: Session, user: User, course_id: UUID) -> None:
    if user.role.code == "teacher" and db.scalar(select(CourseAssignment.id).where(CourseAssignment.course_id == course_id, CourseAssignment.teacher_id == user.id)) is None:
        raise HTTPException(status_code=403, detail="No tienes este curso asignado")


@router.get("/{course_id}/assignments", response_model=list[CourseAssignmentResponse])
def list_course_assignments(course_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "teacher", "coordinator", "director"))) -> list[CourseAssignment]:
    if db.get(Course, course_id) is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    statement = select(CourseAssignment).where(CourseAssignment.course_id == course_id)
    if user.role.code == "teacher": statement = statement.where(CourseAssignment.teacher_id == user.id)
    return db.scalars(statement).all()


@router.post("/{course_id}/assignments", response_model=CourseAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_course(course_id: UUID, payload: CourseAssignmentCreate, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "coordinator"))) -> CourseAssignment:
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
def remove_course_assignment(course_id: UUID, assignment_id: UUID, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "coordinator"))) -> None:
    assignment = db.get(CourseAssignment, assignment_id)
    if assignment is None or assignment.course_id != course_id:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    db.delete(assignment)
    db.commit()


@router.get("/{course_id}/assessment-components", response_model=list[AssessmentComponentResponse])
def list_assessment_components(course_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "teacher", "coordinator", "director"))) -> list[CourseAssessmentComponent]:
    if db.get(Course, course_id) is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    _ensure_course_access(db, user, course_id)
    return db.scalars(select(CourseAssessmentComponent).where(CourseAssessmentComponent.course_id == course_id).order_by(CourseAssessmentComponent.created_at)).all()


@router.post("/{course_id}/assessment-components", response_model=AssessmentComponentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment_component(course_id: UUID, payload: AssessmentComponentCreate, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "coordinator"))) -> CourseAssessmentComponent:
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
def update_assessment_component(course_id: UUID, component_id: UUID, payload: AssessmentComponentUpdate, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "coordinator"))) -> CourseAssessmentComponent:
    component = db.get(CourseAssessmentComponent, component_id)
    if component is None or component.course_id != course_id:
        raise HTTPException(status_code=404, detail="Componente no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(component, field, value)
    db.commit()
    db.refresh(component)
    return component


@router.delete("/{course_id}/assessment-components/{component_id}", response_model=AssessmentComponentResponse)
def deactivate_assessment_component(course_id: UUID, component_id: UUID, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "coordinator"))) -> CourseAssessmentComponent:
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
    user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
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
    _user: User = Depends(require_roles("admin", "coordinator")),
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
    user: User = Depends(require_roles("admin", "teacher", "coordinator", "director")),
) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    _ensure_course_access(db, user, course_id)
    return course


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(course_id: UUID, payload: CourseUpdate, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "coordinator"))) -> Course:
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
def delete_course(course_id: UUID, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "coordinator"))) -> None:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    course.is_active = False
    db.commit()
