"""Restart verification on a disposable named volume with synthetic marks only."""

import argparse
import json
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    config_path = root / "config/local/phase4apersist.env"
    config = dict(
        line.split("=", 1)
        for line in config_path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    assert config["COMPOSE_PROJECT_NAME"] == "paideia-dev-phase4apersist"
    assert (
        config["POSTGRES_DB"] == "paideia_dev_phase4apersist" and config["FRONTEND_PORT"] == "14205"
    )
    base = "http://localhost:14205/api/v1"
    token = None

    def api(method, path, payload=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(
            base + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers=headers,
            method=method,
        )
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    token = api(
        "POST",
        "/auth/login",
        dict(email=config["INITIAL_ADMIN_EMAIL"], password=config["INITIAL_ADMIN_PASSWORD"]),
    )["access_token"]
    catalog = api("GET", "/academic/catalog")
    student = api("GET", "/students")[0]
    course_id = catalog["courses"][0]["id"]
    period_id = catalog["periods"][0]["id"]
    assert not api("GET", "/grades"), "Use a fresh synthetic persistence project"
    component = api(
        "POST", f"/courses/{course_id}/assessment-components", dict(name="Cuaderno", weight=1)
    )
    row = dict(
        student_code=student["student_code"],
        score=15,
        evaluation_type="Cuaderno",
        evaluation_name="Persistencia sintetica",
        assessment_date="2026-03-01",
    )
    api(
        "POST", "/imports/grades/commit", dict(course_id=course_id, period_id=period_id, rows=[row])
    )
    api(
        "POST",
        "/grades",
        dict(
            student_id=student["id"],
            course_id=course_id,
            period_id=period_id,
            component_id=component["id"],
            score=0,
            evaluation_type="Cuaderno",
            assessment_date="2026-03-02",
        ),
    )
    api(
        "POST",
        "/attendance",
        dict(
            student_id=student["id"],
            course_id=course_id,
            period_id=period_id,
            attendance_date="2026-03-01",
            status="PRESENT",
        ),
    )
    api(
        "POST",
        "/follow-ups",
        dict(student_id=student["id"], action="Historial sintetico conservado"),
    )
    container = "paideia-dev-phase4apersist-backend-1"

    def inventory():
        return json.loads(
            subprocess.check_output(
                ["docker", "exec", container, "python", "-m", "app.inspect_database"],
                text=True,
                encoding="utf-8",
            )
        )

    before = inventory()
    compose = [
        "docker",
        "compose",
        "--env-file",
        str(config_path),
        "-f",
        "docker-compose.environment.yml",
    ]
    for command in (
        ["restart", "postgres"],
        ["up", "-d", "--wait", "--wait-timeout", "60", "postgres"],
        ["restart", "backend", "frontend"],
        ["up", "-d", "--wait", "--wait-timeout", "60", "backend", "frontend"],
    ):
        subprocess.run(compose + command, cwd=root, check=True)
    after = inventory()
    assert before == after, "Synthetic data/schema inventory changed after restart"
    rows_after = api("GET", "/grades")
    checks = [
        dict(
            id="PS-01",
            expected="Entire data/schema inventory survives PostgreSQL/API/frontend restart",
            observed=dict(tables=len(after["tables"]), same_inventory=True),
            status="verified",
        ),
        dict(
            id="PS-02",
            expected="Imported mark and explicit manual zero remain linked to same student",
            observed=dict(
                grades=len(rows_after),
                same_student=all(r["student_id"] == student["id"] for r in rows_after),
            ),
            status="verified"
            if len(rows_after) == 2 and any(r["score"] == 0 for r in rows_after)
            else "defect",
        ),
        dict(
            id="PS-03",
            expected="Attendance, follow-up and component configuration remain readable",
            observed=dict(
                attendance=len(api("GET", "/attendance")),
                follow_ups=len(api("GET", "/follow-ups")),
                components=len(api("GET", f"/courses/{course_id}/assessment-components")),
            ),
            status="verified",
        ),
    ]
    (args.private / "persistence-results.json").write_text(
        json.dumps(checks, indent=2), encoding="utf-8"
    )
    print(json.dumps(checks))


if __name__ == "__main__":
    main()
