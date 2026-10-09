"""Actual UI/API/PostgreSQL check; only fresh phase4b2 synthetic environments.

Requires the private Playwright venv and Edge. Never imports an institutional file.
Restarts exclusively the validated synthetic Compose project with its own volume.
"""

import argparse
import csv
import io
import json
import re
import subprocess
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--browser", required=True)
    args = parser.parse_args()
    config = dict(
        line.split("=", 1)
        for line in args.config.read_text(encoding="utf-8-sig").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    project = config["COMPOSE_PROJECT_NAME"]
    assert re.fullmatch(r"paideia-dev-phase4b2[a-z0-9-]*", project)
    alias = project.removeprefix("paideia-dev-")
    assert config["POSTGRES_DB"] == f"paideia_dev_{alias.replace('-', '_')}"
    assert config["POSTGRES_USER"] == "paideia_dev"
    assert 14206 <= int(config["FRONTEND_PORT"]) <= 14219
    assert config["PAIDEIA_ENV_FILE"] == f"config/local/{alias}.env"
    base = f"http://localhost:{config['FRONTEND_PORT']}"
    compose = [
        "docker",
        "compose",
        "--env-file",
        str(args.config),
        "-f",
        "docker-compose.environment.yml",
    ]
    checks = []

    def passed(name, **details):
        checks.append(name)
        print(json.dumps({"check": name, "passed": True, **details}), flush=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True)
        context = browser.new_context()
        context.route(
            "**/*",
            lambda route: route.continue_()
            if route.request.url.startswith(base + "/")
            else route.abort(),
        )
        page = context.new_page()
        page.set_default_timeout(15000)
        page.goto(base + "/login")
        page.locator('input[name="email"]').fill(config["INITIAL_ADMIN_EMAIL"])
        page.locator('input[name="password"]').fill(config["INITIAL_ADMIN_PASSWORD"])
        with page.expect_response(lambda response: "/api/v1/auth/login" in response.url) as reply:
            page.get_by_role("button", name="Iniciar sesión").click()
        assert reply.value.status == 200
        expect(page).not_to_have_url(base + "/login")
        headers = {
            "Authorization": "Bearer "
            + page.evaluate("localStorage.getItem('paideia_access_token')")
        }

        def api(method, endpoint, payload=None):
            response = context.request.fetch(
                base + "/api/v1" + endpoint, method=method, headers=headers, data=payload
            )
            assert response.ok, "Synthetic API request failed"
            return response.json()

        assert api("GET", "/grades") == [], (
            "Use a fresh synthetic project; never reset existing data"
        )
        catalog = api("GET", "/academic/catalog")
        course, period = catalog["courses"][0], catalog["periods"][0]
        student = api("GET", "/students")[0]
        available = api("GET", f"/courses/{course['id']}/assessment-components")
        component = next((item for item in available if item["name"] == "Cuaderno"), None)
        if component is None:
            component = api(
                "POST",
                f"/courses/{course['id']}/assessment-components",
                {"name": "Cuaderno", "weight": 2},
            )
        assert component["weight"] == 2
        assessment_date = subprocess.check_output(
            [
                "docker",
                "exec",
                project + "-backend-1",
                "python",
                "-c",
                "from app.core.database import SessionLocal; "
                "from app.models.academic import AcademicPeriod; "
                "import sys; db=SessionLocal(); "
                "print(db.get(AcademicPeriod, sys.argv[1]).starts_on.isoformat()); db.close()",
                period["id"],
            ],
            text=True,
        ).strip()
        frame = io.StringIO()
        writer = csv.writer(frame)
        writer.writerow(
            [
                "student_code",
                "score",
                "evaluation_name",
                "evaluation_type",
                "assessment_date",
                "qualitative_note",
            ]
        )
        for i in range(10):
            writer.writerow(
                [
                    student["student_code"],
                    i,
                    f"Evaluación sintética 4B2 {i}",
                    "Cuaderno",
                    assessment_date,
                    "",
                ]
            )
        content = frame.getvalue().encode("utf-8")

        def open_import():
            page.goto(base + "/importacion")
            page.get_by_role("button", name="Calificaciones", exact=True).click()
            page.locator("label").filter(has_text=re.compile("^Curso")).locator(
                "select"
            ).select_option(course["id"])
            page.locator("label").filter(has_text=re.compile("^Periodo")).locator(
                "select"
            ).select_option(period["id"])
            with page.expect_response(
                lambda response: "/imports/grades/preview" in response.url
            ) as preview:
                page.locator('input[type="file"]').set_input_files(
                    {"name": "synthetic.csv", "mimeType": "text/csv", "buffer": content}
                )
            assert preview.value.status == 200
            expect(page.get_by_role("heading", name="Vista previa: 10 filas")).to_be_visible()

        def review():
            with page.expect_response(
                lambda response: "/imports/grades/review" in response.url
            ) as reply:
                page.get_by_role("button", name="Revisar registros existentes").click()
            assert reply.value.status == 200
            return reply.value.json()

        def confirm():
            with page.expect_response(
                lambda response: "/imports/grades/commit" in response.url
            ) as reply:
                page.get_by_role("button", name="Confirmar e importar calificaciones").click()
            assert reply.value.status == 200
            return reply.value.json()

        open_import()
        assert all(item["status"] == "new" for item in review()["rows"])
        assert confirm()["imported"] == 10
        initial = api("GET", "/grades")
        assert len(initial) == 10
        assert all(record["assessment_weight"] == 2 for record in initial)
        passed("UI_first_import", imported=10)
        assert all(item["status"] == "identical" for item in review()["rows"])
        result = confirm()
        assert result["imported"] == 0 and result["skipped"] == 10
        assert api("GET", "/grades") == initial
        passed("UI_identical_reimport", total=10)

        target = next(record for record in initial if record["score"] == 0)
        api("PATCH", f"/grades/{target['id']}", {"score": 17})
        review()
        confirm_button = page.get_by_role("button", name="Confirmar e importar calificaciones")
        expect(confirm_button).to_be_disabled()
        page.get_by_label("Decisión fila 1", exact=True).select_option("keep")
        assert confirm()["updated"] == 0
        assert (
            next(record for record in api("GET", "/grades") if record["id"] == target["id"])[
                "score"
            ]
            == 17
        )
        passed("UI_keep_teacher_correction")

        review()
        # Editing a proposed value invalidates the confirmation and requires review.
        score_input = (
            page.locator("section.preview > table")
            .last.locator("tbody tr")
            .first.locator("td input")
            .nth(1)
        )
        score_input.fill("5")
        expect(confirm_button).to_be_disabled()
        score_input.fill("0")
        review()
        page.get_by_label("Decisión fila 1", exact=True).select_option("update")
        assert confirm()["updated"] == 1
        after = api("GET", "/grades")
        assert len(after) == 10
        restored = next(record for record in after if record["id"] == target["id"])
        assert (
            restored["score"] == 0 and restored["assessment_config"] == target["assessment_config"]
        )
        passed("UI_reviewed_update_and_snapshot")
        api(
            "PATCH",
            f"/courses/{course['id']}/assessment-components/{component['id']}",
            {"weight": 7},
        )

        def inventory():
            return json.loads(
                subprocess.check_output(
                    [
                        "docker",
                        "exec",
                        project + "-backend-1",
                        "python",
                        "-m",
                        "app.inspect_database",
                    ],
                    text=True,
                    encoding="utf-8",
                )
            )

        before_restart = inventory()
        assert before_restart["revision"] == "0013_grade_import_identity"
        assert not before_restart["missing_model_tables"]
        assert before_restart["invalid_constraints"] == 0
        assert not any(item.startswith("grade_record_identities.")
                       for item in before_restart["model_differences"])
        for command in (
            ["restart", "postgres"],
            ["up", "-d", "--wait", "--wait-timeout", "60", "postgres"],
            ["restart", "backend", "frontend"],
            ["up", "-d", "--wait", "--wait-timeout", "60", "backend", "frontend"],
        ):
            subprocess.run(
                compose + command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        assert inventory() == before_restart
        assert api("GET", "/grades") == after
        passed("PostgreSQL_backend_frontend_restart", unchanged=True)
        open_import()
        assert all(item["status"] == "identical" for item in review()["rows"])
        assert confirm()["skipped"] == 10
        assert api("GET", "/grades") == after
        passed("UI_reimport_after_restart", total=10)
        browser.close()
    print(json.dumps({"passed_checks": len(checks), "institutional_services_used": False}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Browser failures can contain filled values. Never print their details.
        raise SystemExit(f"Isolated verification failed: {type(error).__name__}") from None
