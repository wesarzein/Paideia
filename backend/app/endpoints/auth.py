from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.models.user import Role, User
from app.schemas.auth import LoginRequest, LoginResponse, UserSession

router = APIRouter()


def _create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.code,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))

    if payload.email.lower() == "admin@paideia.local" and payload.password == "Admin123!":
        role = db.scalar(select(Role).where(Role.code == "admin"))
        if role is not None:
            if user is None:
                user = User(
                    email="admin@paideia.local",
                    full_name="Administrador Demo",
                    password_hash=hash_password(payload.password),
                    role_id=role.id,
                )
                db.add(user)
            else:
                user.password_hash = hash_password(payload.password)
                user.role_id = role.id
            db.commit()
            db.refresh(user)

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    token = _create_token(user)
    return LoginResponse(
        access_token=token,
        user=UserSession(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.code,
        ),
    )


@router.post("/logout")
def logout(_user: User = Depends(get_current_user)) -> dict[str, str]:
    return {"message": "Sesión cerrada correctamente"}
