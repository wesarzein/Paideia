from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import Role, User
from app.schemas.users import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin")),
) -> list[User]:
    users = db.scalars(select(User).order_by(User.full_name)).all()
    return users


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin")),
) -> User:
    role = db.scalar(select(Role).where(Role.code == payload.role_code))
    if role is None:
        raise HTTPException(status_code=400, detail="Rol no válido")

    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing is not None:
        raise HTTPException(status_code=409, detail="El email ya está registrado")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_id=role.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "coordinator", "director"))) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: UUID, payload: UserUpdate, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin"))) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.role_code is not None:
        role = db.scalar(select(Role).where(Role.code == payload.role_code))
        if role is None:
            raise HTTPException(status_code=400, detail="Rol no válido")
        user.role_id = role.id
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin"))) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(user)
    db.commit()
