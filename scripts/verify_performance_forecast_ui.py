"""Read-only forecast journey in the authorized lab, with one reusable synthetic staff account.

Uses Edge and the isolated Playwright venv. Never creates or edits academic records.
Credentials and screenshots remain under config/local.
"""

import json
import re
import secrets
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright
from verify_academic_lab_api import CONFIG, digest, guard_host
from verify_academic_ui import free_memory


def main():
    guard_host()
    # This journey only reads the linear JSON model; no training, sklearn or build.
    # Use the documented 1 GiB read-only BI browser profile, not the combined worker profile.
    assert free_memory() >= 1024 * 1024**2, "Insufficient memory for read-only Edge journey"
    config = dict(
        line.split("=", 1)
        for line in CONFIG.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line and not line.startswith("#")
    )
    base = "http://127.0.0.1:14211"
    assert config["FRONTEND_PORT"] == "14211"
    state_path = CONFIG.parent / "performance-forecast-ui.state.json"
    result_path = CONFIG.parent / "performance-forecast-ui.result.json"
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            headless=True,
        )
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.route(
            "**/*",
            lambda route: route.continue_()
            if route.request.url.startswith(base + "/")
            else route.abort(),
        )
        api = context.request
        login = api.post(
            base + "/api/v1/auth/login",
            data={
                "email": config["INITIAL_ADMIN_EMAIL"],
                "password": config["INITIAL_ADMIN_PASSWORD"],
            },
        )
        assert login.status == 200
        admin = {"Authorization": "Bearer " + login.json()["access_token"]}
        before = api.get(base + "/api/v1/grades", headers=admin).json()
        if state_path.exists():
            actor = json.loads(state_path.read_text(encoding="utf-8"))
        else:
            actor = {
                "email": f"forecast-{uuid4().hex}@paideia.local",
                "password": secrets.token_hex(24),
            }
            created = api.post(
                base + "/api/v1/users",
                headers=admin,
                data={
                    **actor,
                    "full_name": "Verificador sintético IA",
                    "role_code": "coordinator",
                },
            )
            assert created.status == 201, "Synthetic staff account creation failed"
            state_path.write_text(json.dumps(actor), encoding="utf-8")
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base + "/login")
        page.locator('input[name="email"]').fill(actor["email"])
        page.locator('input[name="password"]').fill(actor["password"])
        page.get_by_role("button", name="Iniciar sesión").click()
        expect(page).not_to_have_url(base + "/login")
        page.goto(base + "/ia")
        expect(page.get_by_role("heading", name="IA para el seguimiento")).to_be_visible()
        token = page.evaluate("localStorage.getItem('paideia_access_token')")
        headers = {"Authorization": "Bearer " + token}
        students = api.get(base + "/api/v1/students", headers=headers).json()
        # Select the pupil/course with the most distinct dated observations.
        counts = {}
        for row in before:
            if row.get("assessment_date"):
                counts.setdefault(
                    (row["student_id"], row["course_id"], row["period_id"]), set()
                ).add(row["assessment_date"])
        key = max(counts, key=lambda key: len(counts[key]))
        pupil = next(s for s in students if s["id"] == key[0])
        page.screenshot(
            path=str(CONFIG.parent / "performance-forecast-initial.png"), full_page=True
        )
        page.get_by_label(re.compile("^Grado")).select_option(pupil["grade_id"])
        page.get_by_label(re.compile("^Aula")).select_option(pupil["section_id"])
        page.get_by_label("Periodo de referencia").select_option(key[2])
        page.get_by_label(re.compile("^Curso")).select_option(key[1])
        analyze = page.get_by_role("button", name="Analizar rendimiento")
        expect(analyze).to_be_enabled()
        analyze.click()
        expect(page.get_by_label("Resumen del análisis")).to_be_visible()
        assert page.locator(".estimate").count() > 0, (
            "No real registered history reached prediction"
        )
        page.get_by_label(re.compile("^Analizar")).select_option("student")
        page.get_by_label(re.compile("^Alumno")).select_option(pupil["id"])
        analyze.click()
        expect(page.locator(".result")).to_have_count(1)
        page.get_by_text("Ver historial utilizado", exact=True).click()
        expect(page.get_by_role("table")).to_be_visible()
        page.screenshot(
            path=str(CONFIG.parent / "performance-forecast-desktop.png"), full_page=True
        )
        page.get_by_label(re.compile("^Predecir")).select_option("bimester")
        page.get_by_label("Último bimestre completado").fill("3")
        analyze.click()
        expect(page.get_by_label("Resumen del análisis")).to_be_visible()

        # A server failure must clear the previous result, then allow a real retry.
        def unavailable(route):
            route.fulfill(
                status=503,
                content_type="application/json",
                body=json.dumps({"detail": "Modelo temporalmente no disponible"}),
            )

        page.route("**/academic-ai/forecast?*", unavailable)
        analyze.click()
        expect(page.get_by_role("alert")).to_contain_text("Modelo temporalmente no disponible")
        assert page.locator(".result").count() == 0
        page.unroute("**/academic-ai/forecast?*", unavailable)
        page.get_by_role("button", name="Reintentar análisis").click()
        expect(page.get_by_label("Resumen del análisis")).to_be_visible()
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(CONFIG.parent / "performance-forecast-mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.reload()
        expect(page.get_by_role("heading", name="IA para el seguimiento")).to_be_visible()
        assert not errors, errors
        after = api.get(base + "/api/v1/grades", headers=admin).json()
        assert digest(sorted(before, key=lambda r: r["id"])) == digest(
            sorted(after, key=lambda r: r["id"])
        )
        result_path.write_text(
            json.dumps(
                {
                    "passed": True,
                    "grade_count": len(after),
                    "grade_sha256": digest(sorted(after, key=lambda r: r["id"])),
                    "javascript_errors": errors,
                    "checks": [
                        "classroom",
                        "student",
                        "exam",
                        "bimester",
                        "history",
                        "error_retry",
                        "mobile",
                        "reload",
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        browser.close()
    print("Forecast UI passed; grades preserved")


if __name__ == "__main__":
    main()
