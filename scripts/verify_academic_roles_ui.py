"""Visual role regression in the single synthetic lab; never edits grades.

Creates dedicated synthetic accounts only, links the known synthetic pupil, and
assigns the controlled SYN-UI-4B course. Credentials/evidence stay in config/local.
"""

import json
import re
import secrets
import subprocess
import traceback
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
            "u=make_url(settings.database_url); assert (u.host,u.database,u.username)=="
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
    visual = json.loads((CONFIG.parent / "academic-ui.state.json").read_text(encoding="utf-8"))
    teacher = json.loads(
        (CONFIG.parent / "reports-accounts-ui.state.json").read_text(encoding="utf-8")
    )
    state_path = CONFIG.parent / "academic-roles-ui.state.json"
    state = (
        json.loads(state_path.read_text(encoding="utf-8"))
        if state_path.exists()
        else {
            "actors": {"teacher": teacher},
            "checks": [],
        }
    )

    def save():
        state_path.write_text(json.dumps(state), encoding="utf-8")

    base = "http://127.0.0.1:14211"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            headless=True,
        )
        errors = []

        def session(credentials):
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            context.route(
                "**/*",
                lambda route: route.continue_()
                if route.request.url.startswith(base + "/")
                else route.abort(),
            )
            page = context.new_page()
            page.set_default_timeout(20000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/login")
            page.locator('input[name="email"]').fill(credentials["email"])
            page.locator('input[name="password"]').fill(credentials["password"])
            page.get_by_role("button", name="Iniciar sesión").click()
            expect(page).not_to_have_url(base + "/login")
            headers = {
                "Authorization": "Bearer "
                + page.evaluate("localStorage.getItem('paideia_access_token')")
            }

            def api(method, path, payload=None, status=200):
                response = context.request.fetch(
                    base + "/api/v1" + path, method=method, headers=headers, data=payload
                )
                assert response.status == status, (path, response.status)
                return response.json()

            return context, page, api, headers

        context, page, admin, _headers = session(
            {"email": config["INITIAL_ADMIN_EMAIL"], "password": config["INITIAL_ADMIN_PASSWORD"]}
        )
        before = admin("GET", "/grades")
        assert len(before) == 32
        pupils = admin("GET", "/students")
        pupil = next(row for row in pupils if row["student_code"] == "1SA001")
        outsider = next((row for row in pupils if row["id"] != pupil["id"]), None)
        if outsider is None:
            outsider = admin(
                "POST",
                "/students",
                {
                    "first_name": "Fuera",
                    "last_name": "Del vínculo sintético",
                    "grade_id": pupil["grade_id"],
                    "section_id": pupil["section_id"],
                    "status": "ACTIVE",
                },
                201,
            )
        course = visual["course"]
        assert course["code"] == "SYN-UI-4B"
        assignments = admin("GET", f"/courses/{course['id']}/assignments")
        assert all(
            row["teacher_id"] in (None, teacher["user_id"])
            for row in assignments
            if row["section_id"] == pupil["section_id"]
        ), "Do not overwrite an unrelated assignment"
        admin(
            "POST",
            f"/courses/{course['id']}/assignments",
            {"section_id": pupil["section_id"], "teacher_id": teacher["user_id"]},
            201,
        )
        for role in ("coordinator", "director", "student", "parent"):
            actor = state["actors"].setdefault(
                role,
                {
                    "email": f"ui-{role}-{uuid4().hex[:12]}@paideia.local",
                    "password": secrets.token_hex(16),
                },
            )
            if "user_id" not in actor:
                save()
                if role in ("student", "parent"):
                    field = "student_user_id" if role == "student" else "parent_user_id"
                    assert not pupil[field], "Do not reuse an unrelated family account"
                payload = {
                    "email": actor["email"],
                    "password": actor["password"],
                    "full_name": f"Cuenta sintética {role}",
                    "role_code": role,
                }
                if role == "student":
                    payload["student_id"] = pupil["id"]
                if role == "parent":
                    payload["student_ids"] = [pupil["id"]]
                actor["user_id"] = admin("POST", "/users", payload, 201)["id"]
                save()
        assert admin("GET", "/grades") == before
        context.close()
        for role in ("teacher", "coordinator", "director", "student", "parent"):
            if role in state["checks"]:
                continue
            context, page, api, headers = session(state["actors"][role])
            rows = api("GET", "/grades")
            if role == "teacher":
                assert len(rows) == 11 and {row["course_id"] for row in rows} == {course["id"]}
                forbidden_course = next(
                    row["course_id"] for row in before if row["course_id"] != course["id"]
                )
                assert api("GET", "/grades?course_id=" + forbidden_course) == []
                api(
                    "POST",
                    "/grades",
                    {
                        "student_id": pupil["id"],
                        "course_id": forbidden_course,
                        "period_id": before[0]["period_id"],
                        "assessment_date": "2026-04-01",
                        "score": 0,
                    },
                    403,
                )
            elif role in ("coordinator", "director"):
                assert rows == before
            else:
                assert rows and {row["student_id"] for row in rows} == {pupil["id"]}
                expect(page).to_have_url(base + "/mi-avance")
                expect(page.locator(".student-card")).to_have_count(1)
                expect(page.locator(".student-card")).to_contain_text(pupil["student_code"])
                expect(
                    page.locator(".student-card .table-wrap").first.locator("tbody tr")
                ).to_have_count(len(rows))
                assert api("GET", "/grades?student_id=" + outsider["id"]) == []
                api("GET", "/students/" + outsider["id"], status=403)
                api("GET", "/users", status=403)
                page.goto(base + "/usuarios")
                expect(page).to_have_url(base + "/mi-avance")
            if role in ("teacher", "coordinator", "director"):
                page.goto(base + "/reportes")
                expect(page.get_by_role("heading", name="Reportes académicos")).to_be_visible()
                page.get_by_label(re.compile(r"^Nivel")).select_option("Secundaria")
                page.get_by_label(re.compile(r"^Grado")).select_option(pupil["grade_id"])
                page.get_by_label(re.compile(r"^Curso")).select_option(course["id"])
                page.get_by_label("Mes", exact=True).fill("2026-04")
                report_rows = api(
                    "GET",
                    f"/reports/students?grade_id={pupil['grade_id']}&course_id={course['id']}&month=4",
                )
                expect(page.locator("tbody tr")).to_have_count(len(report_rows))
                with page.expect_download() as download:
                    page.get_by_role("button", name="Exportar Excel", exact=True).click()
                assert download.value.failure() is None
                response = context.request.get(
                    base
                    + f"/api/v1/reports/export.xlsx?grade_id={pupil['grade_id']}"
                    + f"&course_id={course['id']}&month=4",
                    headers=headers,
                )
                assert response.status == 200
                page.goto(base + "/usuarios")
                expect(page).to_have_url(base + "/dashboard")
            context.close()
            state["checks"].append(role)
            save()
        context, _page, admin, _headers = session(
            {"email": config["INITIAL_ADMIN_EMAIL"], "password": config["INITIAL_ADMIN_PASSWORD"]}
        )
        assert admin("GET", "/grades") == before
        assert not errors
        context.close()
        browser.close()
        print(
            json.dumps(
                {
                    "passed": True,
                    "roles": state["checks"],
                    "preserved_grades": len(before),
                    "grades_sha256": digest(before),
                    "javascript_errors": len(errors),
                }
            )
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            json.dumps(
                {
                    "passed": False,
                    "error_type": type(error).__name__,
                    "script_line": traceback.extract_tb(error.__traceback__)[-1].lineno,
                }
            )
        )
        raise SystemExit(1) from None
