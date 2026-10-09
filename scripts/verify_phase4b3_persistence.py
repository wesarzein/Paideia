"""Lightweight API/PostgreSQL restart check for the existing synthetic 4B.3 lab.

This script deliberately has no Playwright dependency. It accepts only the named
phase4b3ui environment, restarts only PostgreSQL, and never creates or removes resources.
"""

import argparse
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT = "paideia-dev-phase4b3ui"


def request(url: str, method="GET", payload=None, token=None):
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(
        urllib.request.Request(url, data=body, headers=headers, method=method), timeout=10
    ) as response:
        return json.load(response)


def inventory() -> dict:
    code = (
        "import json; from app.inspect_database import inventory; "
        "print(json.dumps(inventory(), sort_keys=True))"
    )
    output = subprocess.check_output(
        ["docker", "exec", f"{PROJECT}-backend-1", "python", "-c", code], text=True
    )
    return json.loads(output.strip().splitlines()[-1])


def canonical_grades(grades: list[dict]) -> list[dict]:
    fields = (
        "id", "student_id", "course_id", "period_id", "component_id",
        "evaluation_name", "evaluation_type", "assessment_date", "score",
        "assessment_weight", "assessment_config", "qualitative_note",
    )
    return sorted(
        ({field: grade.get(field) for field in fields} for grade in grades),
        key=lambda grade: grade["id"],
    )


def digest(value) -> str:
    content = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    assert args.config.resolve().name == "phase4b3ui.env"
    config = dict(
        line.split("=", 1)
        for line in args.config.read_text(encoding="utf-8-sig").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    assert config["COMPOSE_PROJECT_NAME"] == PROJECT
    assert config["POSTGRES_DB"] == "paideia_dev_phase4b3ui"
    assert config["POSTGRES_USER"] == "paideia_dev"
    assert config["ALLOW_SYNTHETIC_SEED"].lower() == "true"

    compose = [
        "docker", "compose", "--env-file", str(args.config.resolve()),
        "-f", "docker-compose.environment.yml",
    ]
    base = f"http://127.0.0.1:{config['FRONTEND_PORT']}/api/v1"
    login = request(
        base + "/auth/login",
        method="POST",
        payload={
            "email": config["INITIAL_ADMIN_EMAIL"],
            "password": config["INITIAL_ADMIN_PASSWORD"],
        },
    )
    token = login["access_token"]
    before_grades = canonical_grades(request(base + "/grades", token=token))
    assert len(before_grades) == 10
    assert any(grade["score"] == 5 for grade in before_grades)
    before_inventory = inventory()

    subprocess.run(compose + ["restart", "postgres"], check=True)
    subprocess.run(
        compose + ["up", "-d", "--wait", "--wait-timeout", "60", "postgres"],
        check=True,
    )
    deadline = time.monotonic() + 60
    while True:
        try:
            after_grades = canonical_grades(request(base + "/grades", token=token))
            break
        except (OSError, urllib.error.HTTPError):
            if time.monotonic() >= deadline:
                raise RuntimeError("La API no se recuperó después del reinicio sintético") from None
            time.sleep(2)
    after_inventory = inventory()

    assert after_grades == before_grades
    assert after_inventory == before_inventory
    print(json.dumps({
        "check": "phase4b3_postgres_restart_persistence",
        "passed": True,
        "project": PROJECT,
        "grades": len(after_grades),
        "grades_sha256": digest(after_grades),
        "inventory_sha256": digest(after_inventory),
        "browser_equivalent": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
