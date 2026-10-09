"""Focused local browser checks of account status and missing report evidence.

Uses one synthetic account; preserves every existing grade and stores credentials
only in ignored config/local. Does not reset or delete laboratory resources.
"""

import json
import re
import secrets
import subprocess
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright
from verify_academic_lab_api import CONFIG, PROJECT, digest, guard_host
from verify_academic_ui import free_memory


def main():
    guard_host()
    assert free_memory() >= 1536 * 1024**2, "Insufficient memory for Edge"
    subprocess.run(
        [
            "docker",
            "exec",
            PROJECT + "-backend-1",
            "python",
            "-B",
            "-c",
            "from app.core.config import settings; from app.core.database import engine; "
            "from sqlalchemy.engine import make_url; from sqlalchemy import text; "
            "u=make_url(settings.database_url); "
            "assert (u.host,u.database,u.username)=="
            "('postgres','paideia_dev_phase4b3ui','paideia_dev'); "
            "c=engine.connect(); assert c.execute("
            "text('SELECT current_database(),current_user')).one()=="
            "('paideia_dev_phase4b3ui','paideia_dev'); c.close()",
        ],
        check=True,
    )
    config = dict(
        line.split("=", 1)
        for line in CONFIG.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line and not line.startswith("#")
    )
    base = "http://127.0.0.1:14211"
    state_path = CONFIG.parent / "reports-accounts-ui.state.json"
    state = (
        json.loads(state_path.read_text(encoding="utf-8"))
        if state_path.exists()
        else {
            "email": f"ui-status-{uuid4().hex[:12]}@paideia.local",
            "password": secrets.token_hex(16),
            "checks": [],
        }
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
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
        page = context.new_page()
        page.set_default_timeout(20000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base + "/login")
        page.locator('input[name="email"]').fill(config["INITIAL_ADMIN_EMAIL"])
        page.locator('input[name="password"]').fill(config["INITIAL_ADMIN_PASSWORD"])
        page.get_by_role("button", name="Iniciar sesión").click()
        expect(page).not_to_have_url(base + "/login")
        headers = {
            "Authorization": "Bearer "
            + page.evaluate("localStorage.getItem('paideia_access_token')")
        }

        def api(method, path, payload=None, expected=200):
            response = context.request.fetch(
                base + "/api/v1" + path, method=method, headers=headers, data=payload
            )
            assert response.status == expected, (path, response.status)
            return response.json()

        before = api("GET", "/grades")
        assert len(before) >= 32
        grade_id = next(
            row["grade_id"] for row in api("GET", "/students") if row["student_code"] == "1SA001"
        )
        if "user_id" not in state:
            account = api(
                "POST",
                "/users",
                {
                    "email": state["email"],
                    "password": state["password"],
                    "full_name": "Cuenta sintética de validación visual",
                    "role_code": "teacher",
                },
                201,
            )
            state["user_id"] = account["id"]
            state_path.write_text(json.dumps(state), encoding="utf-8")
        account = api("GET", "/users/" + state["user_id"])
        if not account["is_active"]:
            api("PATCH", "/users/" + state["user_id"], {"is_active": True})
        page.goto(base + "/usuarios")
        row = page.locator("tbody tr").filter(has_text=state["email"])
        expect(row).to_have_count(1)
        row.get_by_role("button", name="Desactivar", exact=True).click()
        with page.expect_response(
            lambda response: response.request.method == "PATCH" and "/users/" in response.url
        ) as reply:
            page.get_by_role("button", name="Confirmar", exact=True).click()
        assert reply.value.status == 200 and reply.value.json()["is_active"] is False
        expect(row.get_by_role("button", name="Reactivar", exact=True)).to_be_visible()
        response = context.request.post(
            base + "/api/v1/auth/login",
            data={"email": state["email"], "password": state["password"]},
        )
        assert response.status == 401
        row.get_by_role("button", name="Reactivar", exact=True).click()
        with page.expect_response(
            lambda response: response.request.method == "PATCH" and "/users/" in response.url
        ) as reply:
            page.get_by_role("button", name="Confirmar", exact=True).click()
        assert reply.value.status == 200 and reply.value.json()["is_active"] is True
        expect(row.get_by_role("button", name="Desactivar", exact=True)).to_be_visible()
        state["checks"] = ["account_status"]
        state_path.write_text(json.dumps(state), encoding="utf-8")

        page.goto(base + "/reportes")
        page.get_by_label(re.compile(r"^Nivel")).select_option("Secundaria")
        page.get_by_label(re.compile(r"^Grado")).select_option(grade_id)
        page.get_by_label("Mes", exact=True).fill("2026-02")
        reports = api("GET", "/reports/students?grade_id=" + grade_id + "&month=2")
        assert reports and all(row["average_score"] is None for row in reports)
        expect(page.locator("tbody tr")).to_have_count(len(reports))
        expect(page.get_by_text("Sin datos", exact=True).first).to_be_visible()
        assert page.locator("tbody tr").filter(has_text="ALTO").count() == 0
        # A failed request has a separate error state, not a fabricated empty report.
        context.route("**/api/v1/reports/students?**", lambda route: route.abort())
        page.get_by_label("Mes", exact=True).fill("2026-03")
        expect(page.get_by_role("alert")).to_contain_text("No se pudo cargar el reporte")
        context.unroute("**/api/v1/reports/students?**")
        page.get_by_label("Mes", exact=True).fill("2026-02")
        expect(page.locator("tbody tr")).to_have_count(len(reports))
        assert api("GET", "/grades") == before
        assert not errors
        state["checks"].append("missing_evidence_reports")
        state_path.write_text(json.dumps(state), encoding="utf-8")
        print(
            json.dumps(
                {
                    "passed": True,
                    "checks": state["checks"],
                    "preserved_grades": len(before),
                    "grades_sha256": digest(before),
                    "javascript_errors": len(errors),
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Filled login controls must never be exposed by a Playwright traceback.
        print(json.dumps({"passed": False, "error_type": type(error).__name__}))
        raise SystemExit(1) from None
