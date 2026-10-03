from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.core.security import hash_password
from app.models.student import Student
from app.models.user import Role, User
from app.schemas.users import UserCreate, UserResponse, UserUpdate

router = APIRouter()


def _serialize_user(db: Session, user: User) -> UserResponse:
    student_id = db.scalar(select(Student.id).where(Student.student_user_id == user.id))
    student_ids = list(
        db.scalars(
            select(Student.id).where(Student.parent_user_id == user.id).order_by(Student.student_code)
        ).all()
    )
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.code,
        student_id=student_id,
        student_ids=student_ids,
        created_at=user.created_at,
    )


def _validate_student_account(db: Session, student_id: UUID, user_id: UUID | None = None) -> Student:
    student = db.get(Student, student_id)
    if student is None or student.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="Selecciona un estudiante activo")
    if student.student_user_id is not None and student.student_user_id != user_id:
        raise HTTPException(status_code=409, detail="El estudiante ya tiene una cuenta vinculada")
    return student


def _validate_parent_students(
    db: Session, student_ids: list[UUID], user_id: UUID | None = None
) -> list[Student]:
    if not student_ids or len(set(student_ids)) != len(student_ids):
        raise HTTPException(status_code=422, detail="Vincula al menos un estudiante activo sin duplicados")
    students = list(db.scalars(select(Student).where(Student.id.in_(student_ids))).all())
    if len(students) != len(student_ids) or any(student.status != "ACTIVE" for student in students):
        raise HTTPException(status_code=422, detail="Todos los estudiantes vinculados deben estar activos")
    if any(student.parent_user_id is not None and student.parent_user_id != user_id for student in students):
        raise HTTPException(status_code=409, detail="Un estudiante ya tiene otro padre o apoderado vinculado")
    return students


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin")),
) -> list[UserResponse]:
    users = db.scalars(select(User).order_by(User.full_name)).all()
    return [_serialize_user(db, user) for user in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin")),
) -> UserResponse:
    role = db.scalar(select(Role).where(Role.code == payload.role_code))
    if role is None:
        raise HTTPException(status_code=400, detail="Rol no válido")
    if db.scalar(select(User.id).where(User.email == payload.email.lower())) is not None:
        raise HTTPException(status_code=409, detail="El email ya está registrado")

    student: Student | None = None
    parent_students: list[Student] = []
    if role.code == "student":
        if payload.student_id is None or payload.student_ids:
            raise HTTPException(status_code=422, detail="Vincula la cuenta de estudiante con un único estudiante")
        student = _validate_student_account(db, payload.student_id)
    elif role.code == "parent":
        if payload.student_id is not None:
            raise HTTPException(status_code=422, detail="Las cuentas de apoderado requieren una lista de estudiantes")
        parent_students = _validate_parent_students(db, payload.student_ids)
    elif payload.student_id is not None or payload.student_ids:
        raise HTTPException(status_code=422, detail="Solo las cuentas de estudiante o apoderado pueden vincular alumnos")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_id=role.id,
    )
    db.add(user)
    try:
        db.flush()
        if student is not None:
            student.student_user_id = user.id
        for linked_student in parent_students:
            linked_student.parent_user_id = user.id
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="La cuenta o el vínculo ya existe") from error
    db.refresh(user)
    return _serialize_user(db, user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "coordinator", "director")),
) -> UserResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _serialize_user(db, user)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin")),
) -> UserResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    old_role = user.role.code
    new_role_code = payload.role_code or old_role
    role = db.scalar(select(Role).where(Role.code == new_role_code))
    if role is None:
        raise HTTPException(status_code=400, detail="Rol no válido")

    fields_set = payload.model_fields_set
    student_id = payload.student_id
    student_ids = payload.student_ids
    if new_role_code == "student":
        if student_ids:
            raise HTTPException(status_code=422, detail="Una cuenta de estudiante solo puede vincular un alumno")
        if "student_id" not in fields_set:
            student_id = db.scalar(select(Student.id).where(Student.student_user_id == user.id))
        if student_id is None:
            raise HTTPException(status_code=422, detail="Vincula la cuenta con un estudiante activo")
        linked_student = _validate_student_account(db, student_id, user.id)
        parent_students: list[Student] = []
    elif new_role_code == "parent":
        if student_id is not None:
            raise HTTPException(status_code=422, detail="Usa la lista de estudiantes para una cuenta de apoderado")
        if "student_ids" not in fields_set:
            student_ids = list(db.scalars(select(Student.id).where(Student.parent_user_id == user.id)).all())
        parent_students = _validate_parent_students(db, student_ids or [], user.id)
        linked_student = None
    else:
        if student_id is not None or student_ids:
            raise HTTPException(status_code=422, detail="Este rol no puede vincular estudiantes")
        linked_student = None
        parent_students = []

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    user.role_id = role.id

    try:
        db.execute(
            update(Student)
            .where(Student.student_user_id == user.id)
            .values(student_user_id=None)
        )
        db.execute(
            update(Student)
            .where(Student.parent_user_id == user.id)
            .values(parent_user_id=None)
        )
        if linked_student is not None:
            linked_student.student_user_id = user.id
        for linked_student in parent_students:
            linked_student.parent_user_id = user.id
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo guardar el vínculo de estudiantes") from error
    db.refresh(user)
    return _serialize_user(db, user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin")),
) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(user)
    db.commit()
