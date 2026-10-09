"""Generate private configuration for a new, independent developer environment."""

import argparse
import re
import secrets
from pathlib import Path


def create_config(root: Path, name: str, port: int) -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,23}", name):
        raise ValueError(
            "Use un alias de 1 a 24 caracteres: letras minúsculas, números o guiones"
        )
    if not 1024 <= port <= 65535 or port in (4200, 5432, 8000):
        raise ValueError(
            "Elija un puerto libre entre 1024 y 65535, distinto de 4200/5432/8000"
        )
    destination = root / "config" / "local" / f"{name}.env"
    destination.parent.mkdir(parents=True, exist_ok=True)
    db_name = f"paideia_dev_{name.replace('-', '_')}"
    password = secrets.token_hex(24)
    content = (
        f"COMPOSE_PROJECT_NAME=paideia-dev-{name}\n"
        f"PAIDEIA_ENV_FILE=config/local/{name}.env\n"
        "ENVIRONMENT=development\n"
        f"FRONTEND_PORT={port}\n"
        f"POSTGRES_DB={db_name}\nPOSTGRES_USER=paideia_dev\nPOSTGRES_PASSWORD={password}\n"
        f"DATABASE_URL=postgresql+psycopg://paideia_dev:{password}@postgres:5432/{db_name}\n"
        f"JWT_SECRET_KEY={secrets.token_hex(32)}\n"
        f"BACKEND_CORS_ORIGINS=http://localhost:{port}\n"
        "INITIAL_ADMIN_EMAIL=admin@paideia-dev.example.com\n"
        f"INITIAL_ADMIN_PASSWORD={secrets.token_urlsafe(24)}\n"
        "INITIAL_ADMIN_FULL_NAME=Administrador sintético\n"
        "ALLOW_SYNTHETIC_SEED=true\nTZ=America/Lima\n"
    )
    with destination.open("x", encoding="utf-8") as config:
        destination.chmod(0o600)
        config.write(content)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Alias del desarrollador o checkout")
    parser.add_argument("--port", type=int, default=14200)
    args = parser.parse_args()
    try:
        path = create_config(Path(__file__).resolve().parents[1], args.name, args.port)
    except (ValueError, FileExistsError) as error:
        parser.exit(1, f"No se generó configuración: {error}\n")
    print(
        f"Configuración privada creada: {path.relative_to(Path(__file__).resolve().parents[1])}"
    )
    print(
        "Los secretos no se muestran. Consulte la guía de Fase 3 para iniciar el entorno."
    )


if __name__ == "__main__":
    main()
