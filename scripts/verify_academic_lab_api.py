"""Low-memory HTTP/XLSX journey for the sole authorized synthetic laboratory.

Run on the host with --stage import|persistence|reimport|configuration.
Uses the backend's internal HTTP port, without publishing PostgreSQL/API ports.
Never deletes data; import requires an empty grade inventory. Configuration uses
the second synthetic course so the original ten records remain distinguishable.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT = "paideia-dev-phase4b3ui"
CONFIG = Path("config/local/phase4b3ui.env")
COMPOSE = [
    "docker",
    "compose",
    "--env-file",
    str(CONFIG),
    "-f",
    "docker-compose.environment.yml",
]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def guard_host():
    config = dict(
        line.split("=", 1)
        for line in CONFIG.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line and not line.startswith("#")
    )
    assert config["COMPOSE_PROJECT_NAME"] == PROJECT
    assert config["PAIDEIA_ENV_FILE"] == CONFIG.as_posix()
    assert config["POSTGRES_DB"] == "paideia_dev_phase4b3ui"
    assert config["POSTGRES_USER"] == "paideia_dev"
    assert config["ALLOW_SYNTHETIC_SEED"] == "true"
    for service in ("postgres", "backend"):
        item = json.loads(
            subprocess.check_output(["docker", "inspect", f"{PROJECT}-{service}-1"], text=True)
        )[0]
        labels = item["Config"]["Labels"]
        assert labels["com.docker.compose.project"] == PROJECT
        assert labels["com.docker.compose.service"] == service
        assert (
            Path(labels["com.docker.compose.project.config_files"]).resolve()
            == Path("docker-compose.environment.yml").resolve()
        )
        if service == "postgres":
            assert any(
                m.get("Name") == PROJECT + "_postgres_data"
                and m["Destination"] == "/var/lib/postgresql/data"
                for m in item["Mounts"]
            )


def inside(stage):
    import httpx
    from sqlalchemy import text
    from sqlalchemy.engine import make_url

    from app.core.config import settings
    from app.core.database import engine
    from app.inspect_database import inventory

    url = make_url(settings.database_url)
    assert (url.host, url.database, url.username) == (
        "postgres",
        "paideia_dev_phase4b3ui",
        "paideia_dev",
    )
    assert settings.environment == "development"
    with engine.connect() as connection:
        assert connection.execute(text("SELECT current_database(),current_user")).one() == (
            "paideia_dev_phase4b3ui",
            "paideia_dev",
        )
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == (
            "0014_evaluation_configuration_revisions"
        )

    client = httpx.Client(base_url="http://127.0.0.1:8000/api/v1", timeout=30)
    login = client.post(
        "/auth/login",
        json={
            "email": settings.initial_admin_email,
            "password": settings.initial_admin_password,
        },
    )
    assert login.status_code == 200, "Synthetic login failed"
    client.headers["Authorization"] = "Bearer " + login.json()["access_token"]

    def api(method, path, payload=None, status=200, **kwargs):
        response = client.request(method, path, json=payload, **kwargs)
        assert response.status_code == status, (
            path,
            response.status_code,
            response.text,
        )
        return response.json()

    def grades():
        return sorted(api("GET", "/grades"), key=lambda row: row["id"])

    def original_payload():
        saved = globals().get("SAVED_PAYLOAD")
        if saved is not None:
            return saved
        # Recover only this exact synthetic fixture after backend recreation.
        # The host then preserves it outside the container's temporary layer.
        records = [row for row in grades() if row["evaluation_revision_id"] is None]
        assert len(records) == 10 and len({row["course_id"] for row in records}) == 1
        sys.path.insert(0, "/app/tests/unit")
        from institutional_fixture import workbook_bytes

        student = next(s for s in api("GET", "/students") if s["student_code"] == "1SA001")
        assert all(row["student_id"] == student["id"] for row in records)
        preview = api(
            "POST",
            "/imports/grades/preview",
            files={"file": ("phase4b3.synthetic.xlsx", workbook_bytes(changes={"C7": 5}))},
        )
        for row in preview["rows"]:
            row.update(student_code="1SA001", student_confirmed=True)
        return {
            "course_id": records[0]["course_id"],
            "period_id": records[0]["period_id"],
            "rows": preview["rows"],
            "academic_context": {
                "school_year": 2026,
                "bimestre": 1,
                "confirmed": True,
                "grade_id": student["grade_id"],
                "section_id": student["section_id"],
                "blocks": {
                    str(block): {
                        "assessment_date": next(
                            r["assessment_date"] for r in records if r["evaluation_block"] == block
                        ),
                        "evaluation_name": next(
                            r["evaluation_name"] for r in records if r["evaluation_block"] == block
                        ),
                    }
                    for block in (1, 2)
                },
            },
        }

    if stage == "snapshot":
        records = grades()
        payload = original_payload()
        original_course = payload["course_id"]
        original = [row for row in records if row["course_id"] == original_course]
        return {
            "grades": original,
            "all_grades": records,
            "inventory": inventory(),
            "_payload": payload,
        }
    if stage == "reimport":
        before = grades()
        payload = original_payload()
        review = api("POST", "/imports/grades/review", payload)
        assert all(row["status"] == "identical" for row in review["rows"])
        result = api("POST", "/imports/grades/commit", payload)
        assert result["skipped"] == 10 and result["imported"] == 0
        assert grades() == before
        return {
            "check": "reimport_after_restart",
            "passed": True,
            "skipped": 10,
            "_payload": payload,
        }

    sys.path.insert(0, "/app/tests/unit")
    from institutional_fixture import workbook_bytes

    catalog = api("GET", "/academic/catalog")
    student = next(s for s in api("GET", "/students") if s["student_code"] == "1SA001")
    course = catalog["courses"][0 if stage == "import" else 1]
    period = catalog["periods"][0]
    scope = f"/courses/{course['id']}"
    context = {
        "school_year": 2026,
        "bimestre": 1,
        "confirmed": True,
        "grade_id": student["grade_id"],
        "section_id": student["section_id"],
        "blocks": {
            "1": {
                "evaluation_name": "Bloque abril confirmado",
                "assessment_date": "2026-04-01",
            },
            "2": {
                "evaluation_name": "Bloque mayo confirmado",
                "assessment_date": "2026-04-29",
            },
        },
    }
    if stage == "import":
        assert grades() == [], "Fresh synthetic grade inventory required; never reset"
        components = api("GET", scope + "/assessment-components")
        if not any(item["name"] == "Cuaderno" for item in components):
            api(
                "POST",
                scope + "/assessment-components",
                {"name": "Cuaderno", "weight": 2},
                status=201,
            )
    else:
        before = grades()
        current = api(
            "GET",
            scope + "/evaluation-configurations/current",
            params={"period_id": period["id"]},
        )
        assert current["version"] == 0, "Configuration journey must not overwrite prior work"
        document = current["configuration"]
        document["template_id"] = "custom_v1"
        document["criteria"][0]["weight"] = 3
        revision_payload = {
            "configuration": document,
            "expected_version": 0,
            "reason": "Validación sintética segunda laptop",
        }
        draft = api("POST", scope + "/evaluation-configurations/drafts", revision_payload, 201)
        active = api(
            "GET",
            scope + "/evaluation-configurations/active",
            params={"period_id": period["id"]},
        )
        assert active["state"] == "default" and grades() == before
        api("POST", scope + "/evaluation-configurations/publish", revision_payload, 409)
        revision_payload["expected_version"] = draft["version"]
        published = api("POST", scope + "/evaluation-configurations/publish", revision_payload, 201)
        revision_payload["expected_version"] = published["version"]
        document["criteria"][0]["weight"] = 9
        api("POST", scope + "/evaluation-configurations/drafts", revision_payload, 201)
        active = api(
            "GET",
            scope + "/evaluation-configurations/active",
            params={"period_id": period["id"]},
        )
        assert active["id"] == published["id"] and grades() == before

    content = workbook_bytes(changes={"C7": 25, "A7": "EXTERNO", "B7": "SINTETICO, AMBIGUO"})
    preview = api(
        "POST",
        "/imports/grades/preview",
        files={
            "file": (
                "phase4b3.synthetic.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert preview["total"] == 10 and preview["errors"]
    assert preview["institutional"]["blank_inputs"] == 150
    assert len(preview["institutional"]["derived"]) == 64
    assert all(not row["assessment_date"] for row in preview["rows"])
    payload = {
        "course_id": course["id"],
        "period_id": period["id"],
        "academic_context": context,
        "rows": preview["rows"],
    }
    api("POST", "/imports/grades/review", payload, 422)
    for row in payload["rows"]:
        row.update(student_code="1SA001", student_confirmed=True)
    payload["rows"][0]["score"] = 0
    review = api("POST", "/imports/grades/review", payload)
    assert not review["errors"]
    assert api("POST", "/imports/grades/commit", payload)["imported"] == 10
    saved = grades()
    imported = [row for row in saved if row["course_id"] == course["id"]]
    assert len(imported) == 10 and sorted(row["score"] for row in imported) == (
        [0, 12, 14, 16, 18, 20, 20, 20, 20, 20]
    )
    assert all(row["assessment_config"] for row in imported)
    assert api("POST", "/imports/grades/commit", payload)["skipped"] == 10
    assert grades() == saved
    if stage == "import":
        first = next(row for row in imported if row["score"] == 0)
        api("PATCH", f"/grades/{first['id']}", {"score": 17})
        api("POST", "/imports/grades/commit", payload, 409)
        payload["rows"][0]["decision"] = "keep"
        assert api("POST", "/imports/grades/commit", payload)["skipped"] == 10
        payload["rows"][0]["score"] = 5
        review = api("POST", "/imports/grades/review", payload)
        payload["rows"][0].update(decision="update", review_token=review["rows"][0]["review_token"])
        assert api("POST", "/imports/grades/commit", payload)["updated"] == 1
        final = grades()
        corrected = next(row for row in final if row["id"] == first["id"])
        assert (
            corrected["score"] == 5 and corrected["assessment_config"] == first["assessment_config"]
        )
        assert {row["id"] for row in final} == {row["id"] for row in saved}
        payload["rows"][0].pop("review_token")
        payload["rows"][0].pop("decision")
        return {
            "check": "xlsx_mapping_confirmation_correction",
            "passed": True,
            "grades": 10,
            "grades_sha256": digest(final),
            "_payload": payload,
        }

    assert all(row["evaluation_revision_id"] == published["id"] for row in imported)
    assert (
        next(row for row in imported if row["evaluation_criterion_key"] == "b1_actitud")[
            "assessment_weight"
        ]
        == 3
    )
    manual = {
        "student_id": student["id"],
        "course_id": course["id"],
        "period_id": period["id"],
        "evaluation_name": "Manual explícita segunda laptop",
        "evaluation_type": "Cuaderno",
        "assessment_date": "2026-04-01",
        "score": 14,
    }
    api("POST", "/grades", manual, 422)
    manual.update(academic_bimester=1, evaluation_block=1, evaluation_criterion_key="b1_cuaderno")
    new_grade = api("POST", "/grades", manual, 201)
    assert new_grade["evaluation_revision_id"] == published["id"]
    history_before = grades()
    revision_payload["expected_version"] = 3
    api("POST", scope + "/evaluation-configurations/publish", revision_payload, 201)
    api(
        "POST",
        scope + "/evaluation-configurations/restore-institutional",
        {
            "period_id": period["id"],
            "expected_version": 4,
            "reason": "Restauración sintética",
        },
        201,
    )
    assert grades() == history_before
    assert api("POST", "/imports/grades/commit", payload)["skipped"] == 10
    assert grades() == history_before
    versions = api(
        "GET",
        scope + "/evaluation-configurations/versions",
        params={"period_id": period["id"]},
    )
    assert len(versions) == 5
    return {
        "check": "published_only_manual_xlsx_restore_history",
        "passed": True,
        "imported": 10,
        "manual": 1,
        "versions": 5,
    }


def host(stage):
    guard_host()
    payload_path = CONFIG.parent / "phase4b3.synthetic.payload.json"

    def run_inside(value):
        source = Path(__file__).read_text(encoding="utf-8")
        if payload_path.exists():
            source = "SAVED_PAYLOAD = " + repr(json.loads(payload_path.read_text())) + "\n" + source
        result = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                PROJECT + "-backend-1",
                "python",
                "-B",
                "-",
                "--inside",
                "--stage",
                value,
            ],
            input=source,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
        output = json.loads(result.stdout)
        if "_payload" in output:
            payload_path.write_text(json.dumps(output.pop("_payload")), encoding="utf-8")
        return output

    if stage != "persistence":
        return run_inside(stage)
    before = run_inside("snapshot")
    assert len(before["grades"]) == 10 and any(row["score"] == 5 for row in before["grades"])
    guard_host()
    subprocess.run(COMPOSE + ["restart", "postgres"], check=True, capture_output=True)
    deadline = time.monotonic() + 90
    while True:
        try:
            after = run_inside("snapshot")
            break
        except RuntimeError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)
    assert after == before
    return {
        "check": "second_laptop_postgres_restart",
        "passed": True,
        "grades": 10,
        "grades_sha256": digest(after["grades"]),
        "inventory_sha256": digest(after["inventory"]),
        "browser_equivalent": False,
        "previous_laptop_volume_verified": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        required=True,
        choices=["import", "persistence", "reimport", "configuration", "snapshot"],
    )
    parser.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    print(json.dumps(inside(args.stage) if args.inside else host(args.stage), sort_keys=True))
