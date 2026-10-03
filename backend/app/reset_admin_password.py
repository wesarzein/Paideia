from getpass import getpass
from hmac import compare_digest

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import Role, User


def main() -> None:
    email = input("Correo de la cuenta administradora: ").strip().lower()
    password = getpass("Nueva contraseña (mínimo 12 caracteres): ")
    confirmation = getpass("Repite la nueva contraseña: ")

    if len(password) < 12:
        raise SystemExit("La contraseña debe tener al menos 12 caracteres.")
    if not compare_digest(password, confirmation):
        raise SystemExit("Las contraseñas no coinciden.")

    with SessionLocal() as db:
        user = db.scalar(
            select(User)
            .join(Role, User.role_id == Role.id)
            .where(User.email == email, Role.code == "admin")
        )
        if user is None:
            raise SystemExit("No existe una cuenta administradora con ese correo.")

        user.password_hash = hash_password(password)
        db.commit()

    print("Contraseña de administrador actualizada.")


if __name__ == "__main__":
    main()
