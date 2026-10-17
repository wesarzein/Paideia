from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import AuditLog, Role, User
from app.schemas.users import UserCreate, UserResponse, UserUpdate

router = APIRouter()
SCHOOL_ROLE_CODES = {"admin", "teacher", "coordinator"}


def _serialize_user(db: Session, user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.code,
        is_active=user.is_active,
        student_id=None,
        student_ids=[],
        created_at=user.created_at,
    )


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin")),
) -> list[UserResponse]:
    users = db.scalars(select(User).join(Role).where(Role.code.in_(SCHOOL_ROLE_CODES)).order_by(User.full_name)).all()
    return [_serialize_user(db, user) for user in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin")),
) -> UserResponse:
    role = db.scalar(select(Role).where(Role.code == payload.role_code, Role.code.in_(SCHOOL_ROLE_CODES)))
    if role is None:
        raise HTTPException(status_code=400, detail="Rol no válido")
    if db.scalar(select(User.id).where(User.email == payload.email.lower())) is not None:
        raise HTTPException(status_code=409, detail="El email ya está registrado")

    if payload.student_id is not None or payload.student_ids:
        raise HTTPException(
            status_code=422,
            detail="Las cuentas institucionales no se vinculan a alumnos",
        )

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_id=role.id,
    )
    db.add(user)
    try:
        db.flush()
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
    _user: User = Depends(require_roles("admin", "coordinator")),
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
    if "is_active" in payload.model_fields_set:
        if payload.is_active is None:
            raise HTTPException(status_code=422, detail="El estado no admite null")
        _set_account_status(db, user, payload.is_active, _user)
        if payload.model_fields_set == {"is_active"}:
            db.commit()
            db.refresh(user)
            return _serialize_user(db, user)
    new_role_code = payload.role_code or old_role
    role = db.scalar(select(Role).where(Role.code == new_role_code, Role.code.in_(SCHOOL_ROLE_CODES)))
    if role is None:
        raise HTTPException(status_code=400, detail="Rol no válido")

    if payload.student_id is not None or payload.student_ids:
        raise HTTPException(status_code=422, detail="Las cuentas institucionales no se vinculan a alumnos")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    user.role_id = role.id

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="No se pudo guardar el vínculo de estudiantes"
        ) from error
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
    _set_account_status(db, user, False, _user)
    db.commit()


def _set_account_status(db: Session, user: User, active: bool, actor: User) -> None:
    if user.is_active == active:
        return
    if not active and user.role.code == "admin":
        # Serialize deactivations so two administrators cannot deactivate the
        # remaining active administrators concurrently.
        db.scalars(
            select(User)
            .join(Role)
            .where(Role.code == "admin")
            .order_by(User.id)
            .with_for_update(of=User)
        ).all()
        active_admins = db.scalar(
            select(func.count(User.id))
            .join(Role)
            .where(Role.code == "admin", User.is_active.is_(True))
        )
        if active_admins <= 1:
            raise HTTPException(status_code=409, detail="Debe conservarse un administrador activo")
    user.is_active = active
    db.add(
        AuditLog(
            actor_email=actor.email,
            action="USER_REACTIVATED" if active else "USER_DEACTIVATED",
            entity="users",
            details=str(user.id),
        )
    )
