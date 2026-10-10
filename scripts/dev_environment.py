"""Start, stop or update one private synthetic environment without deleting data."""

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def configuration(path):
    path = Path(path).resolve()
    if path.parent != ROOT / "config" / "local" or path.suffix != ".env":
        raise ValueError("Use exclusivamente config/local/<alias>.env")
    alias = path.stem
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,23}", alias):
        raise ValueError("Alias privado inválido")
    values = dict(
        line.split("=", 1)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line and not line.startswith("#")
    )
    expected = {
        "COMPOSE_PROJECT_NAME": "paideia-dev-" + alias,
        "PAIDEIA_ENV_FILE": path.relative_to(ROOT).as_posix(),
        "ENVIRONMENT": "development",
        "POSTGRES_USER": "paideia_dev",
        "POSTGRES_DB": "paideia_dev_" + alias.replace("-", "_"),
        "ALLOW_SYNTHETIC_SEED": "true",
    }
    if any(values.get(key) != value for key, value in expected.items()):
        raise ValueError("Configuración ajena al entorno sintético independiente")
    url = urlsplit(values.get("DATABASE_URL", ""))
    if (
        (url.scheme, url.hostname, url.username, url.path, url.password)
        != (
            "postgresql+psycopg",
            "postgres",
            "paideia_dev",
            "/" + expected["POSTGRES_DB"],
            values.get("POSTGRES_PASSWORD"),
        )
        or url.query
        or url.fragment
        or url.port not in (None, 5432)
        or not url.password
    ):
        raise ValueError("Destino DATABASE_URL no corresponde al PostgreSQL propio")
    if values.get("FRONTEND_BIND_ADDRESS", "127.0.0.1") != "127.0.0.1":
        raise ValueError("El entorno cotidiano debe escuchar solo en localhost")
    return path, values


def execute(args, capture=False):
    result = subprocess.run(
        args, cwd=ROOT, text=True, capture_output=capture, check=True
    )
    return result.stdout if capture else None


def provenance(project, values=None):
    ids = execute(
        [
            "docker",
            "ps",
            "-aq",
            "--filter",
            "label=com.docker.compose.project=" + project,
        ],
        True,
    ).split()
    if ids:
        for item in json.loads(execute(["docker", "inspect", *ids], True)):
            labels = item["Config"]["Labels"]
            if (
                Path(
                    labels.get("com.docker.compose.project.config_files", "")
                ).resolve()
                != ROOT / "docker-compose.environment.yml"
            ):
                raise ValueError(
                    "Proyecto existente creado con otro Compose; no se modifica"
                )
            if labels.get("com.docker.compose.service") == "postgres":
                existing = dict(
                    entry.split("=", 1)
                    for entry in item["Config"]["Env"]
                    if "=" in entry
                )
                if values and any(
                    existing.get(key) != values[key]
                    for key in ("POSTGRES_DB", "POSTGRES_USER")
                ):
                    raise ValueError(
                        "La configuración no coincide con el PostgreSQL existente"
                    )
                mounts = [
                    m
                    for m in item["Mounts"]
                    if m["Destination"] == "/var/lib/postgresql/data"
                ]
                if (
                    len(mounts) != 1
                    or mounts[0].get("Name") != project + "_postgres_data"
                ):
                    raise ValueError("Volumen PostgreSQL ajeno; no se modifica")
    volumes = execute(["docker", "volume", "ls", "-q"], True).split()
    volume = project + "_postgres_data"
    if volume in volumes:
        labels = (
            json.loads(execute(["docker", "volume", "inspect", volume], True))[0].get(
                "Labels"
            )
            or {}
        )
        if (
            labels.get("com.docker.compose.project") != project
            or labels.get("com.docker.compose.volume") != "postgres_data"
        ):
            raise ValueError("Procedencia del volumen no acreditada")


def run(path, action):
    path, values = configuration(path)
    project = values["COMPOSE_PROJECT_NAME"]
    provenance(project, values)
    compose = [
        "docker",
        "compose",
        "--env-file",
        str(path),
        "-f",
        str(ROOT / "docker-compose.environment.yml"),
    ]
    effective = json.loads(execute(compose + ["config", "--format", "json"], True))
    services = effective["services"]
    if (
        effective["name"] != project
        or effective["volumes"]["postgres_data"]["name"] != project + "_postgres_data"
        or services["backend"]["image"] != project + "-backend"
        or services["backend"]["environment"]["DATABASE_URL"] != values["DATABASE_URL"]
        or any(
            services["postgres"]["environment"][key] != values[key]
            for key in ("POSTGRES_DB", "POSTGRES_USER")
        )
    ):
        raise ValueError("Variables heredadas alteran el destino efectivo de Compose")
    if action == "status":
        execute(compose + ["ps"])
        return
    if action == "stop":
        execute(compose + ["stop", "frontend", "backend", "postgres"])
        return
    # Never rebuild implicitly, import a roster, reset data or run downgrade.
    execute(compose + ["up", "-d", "--no-build", "--wait", "postgres"])
    guard = (
        "from sqlalchemy import create_engine,text; from app.core.config import settings; "
        "from app.seed_dev import ensure_development_target; ensure_development_target(); "
        "from sqlalchemy.engine import make_url; u=make_url(settings.database_url); "
        'assert (u.host,u.database,u.username)==("postgres",'
        + repr(values["POSTGRES_DB"])
        + ',"paideia_dev"); '
        "c=create_engine(u).connect(); "
        'assert c.execute(text("SELECT current_database(),current_user,current_schema()")).one()=='
        "(" + repr(values["POSTGRES_DB"]) + ',"paideia_dev","public"); c.close(); '
    )
    if action == "initialize":
        empty_guard = guard + (
            "c=create_engine(u).connect(); "
            "students=c.scalar(text(\"SELECT to_regclass('public.students')\")); "
            "grades=c.scalar(text(\"SELECT to_regclass('public.grade_records')\")); "
            'assert students is None or c.scalar(text("SELECT count(*) FROM students"))==0; '
            'assert grades is None or c.scalar(text("SELECT count(*) FROM grade_records"))==0; c.close()'
        )
        execute(
            compose
            + [
                "run",
                "--rm",
                "-T",
                "--no-deps",
                "--entrypoint",
                "python",
                "migrate",
                "-c",
                empty_guard,
            ]
        )
    if action in {"update", "initialize"}:
        # Stop requests before an additive migration; PostgreSQL and volume stay intact.
        execute(compose + ["stop", "frontend", "backend"])
        guard += 'from alembic import command; from alembic.config import Config; command.upgrade(Config("alembic.ini"),"head")'
    else:
        guard += (
            "from alembic.config import Config; from alembic.script import ScriptDirectory; "
            "c=create_engine(u).connect(); "
            'assert c.scalar(text("SELECT version_num FROM alembic_version"))=='
            'ScriptDirectory.from_config(Config("alembic.ini")).get_current_head(); c.close()'
        )
    execute(
        compose
        + [
            "run",
            "--rm",
            "-T",
            "--no-deps",
            "--entrypoint",
            "python",
            "migrate",
            "-c",
            guard,
        ]
    )
    if action == "initialize":
        seed_guard = guard.split("from alembic import command;")[0]
        seed_guard += (
            "c=create_engine(u).connect(); "
            'assert c.scalar(text("SELECT count(*) FROM students"))==0; '
            'assert c.scalar(text("SELECT count(*) FROM grade_records"))==0; c.close(); '
            "from app.seed_dev import main; main()"
        )
        execute(
            compose
            + [
                "run",
                "--rm",
                "-T",
                "--no-deps",
                "--entrypoint",
                "python",
                "seed",
                "-c",
                seed_guard,
            ]
        )
    execute(compose + ["up", "-d", "--no-build", "--wait", "backend", "frontend"])
    print("Entorno propio saludable; datos y volumen conservados.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config")
    parser.add_argument(
        "action", choices=["initialize", "start", "update", "stop", "status"]
    )
    args = parser.parse_args()
    try:
        run(args.config, args.action)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError):
        parser.exit(
            1,
            "Operación detenida: compruebe configuración, procedencia, imágenes y destino. No se eliminaron datos.\n",
        )


if __name__ == "__main__":
    main()
