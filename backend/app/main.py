import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import Role, User
from app.services.school_roster import load_roster, synchronize_roster

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        version=settings.api_version,
        description="API para seguimiento y prevencion del riesgo academico institucional.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.on_event("startup")
    def initialize_application_data() -> None:
        with SessionLocal() as db:
            for role_code, role_name in (
                ("admin", "Administrador"),
                ("teacher", "Docente"),
                ("coordinator", "Coordinador"),
                ("director", "Directivo"),
                ("student", "Estudiante"),
                ("parent", "Padre o apoderado"),
            ):
                if db.scalar(select(Role).where(Role.code == role_code)) is None:
                    db.add(Role(code=role_code, name=role_name))
            db.flush()
            role = db.scalar(select(Role).where(Role.code == "admin"))
            if role is None:
                role = Role(code="admin", name="Administrador")
                db.add(role)
                db.flush()
            if bool(settings.initial_admin_email) != bool(settings.initial_admin_password):
                raise RuntimeError("Configura INITIAL_ADMIN_EMAIL e INITIAL_ADMIN_PASSWORD juntos")
            if settings.initial_admin_email and settings.initial_admin_password:
                initial_email = settings.initial_admin_email.strip().lower()
                user = db.scalar(select(User).where(User.email == initial_email))
                if user is None:
                    db.add(
                        User(
                            email=initial_email,
                            full_name=settings.initial_admin_full_name.strip() or "Administrador",
                            password_hash=hash_password(settings.initial_admin_password),
                            role_id=role.id,
                        )
                    )
                elif user.role.code != "admin":
                    raise RuntimeError("INITIAL_ADMIN_EMAIL ya pertenece a una cuenta que no es administradora")
            else:
                logger.info("No se configuró el alta inicial de administrador; se conserva la gestión de cuentas existentes")
            db.commit()
            roster = load_roster()
            if roster is None:
                logger.warning("Padrón local no encontrado; se omite la conciliación de estudiantes y cursos")
            else:
                counts = synchronize_roster(db, roster)
                logger.info("Padrón 2026 sincronizado desde archivo local: %s", counts)

    return app


app = create_app()
