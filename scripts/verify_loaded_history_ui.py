"""Read-only staff journeys after the explicit private workbook import.

Issues short-lived lab test sessions without changing passwords. No credentials,
student names, marks or screenshots are published; evidence stays in config/local.
"""

import json
import re
import subprocess
from io import BytesIO
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from verify_academic_lab_api import CONFIG, PROJECT, guard_host
from verify_academic_ui import free_memory


def assert_presentation(page):
    visible = page.locator("body").inner_text()
    values = page.locator("input, textarea").evaluate_all("els => els.map(e => e.value).join(' ')")
    match = re.search(r"simulad|sint[ée]tic|fictici|demostraci[oó]n", visible + values, re.I)
    if match:
        elements = page.locator("body *").evaluate_all(
            "els => els.filter(e => !e.children.length && /simulad|sint[ée]tic|fictici|demostraci[oó]n/i.test(e.textContent + (e.value || '')))"
            ".map(e => ({tag: e.tagName, css: e.className, parent: e.parentElement.className}))"
        )
        raise AssertionError((page.url, match.group(), elements))


def main():
    guard_host()
    assert free_memory() >= 1024 * 1024**2, "Insufficient memory for read-only browser"
    code = """
import json
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.user import User,Role
from app.endpoints.auth import _create_token
from app.core.config import settings
from sqlalchemy.engine import make_url
u=make_url(settings.database_url)
assert (u.host,u.database,u.username)==('postgres','paideia_dev_phase4b3ui','paideia_dev')
result={}
with SessionLocal() as db:
    for role in ('admin','teacher','coordinator'):
        user=db.scalars(select(User).join(Role).where(Role.code==role,User.is_active.is_(True))).first()
        assert user is not None
        result[role]={'access_token':_create_token(user),'user':{'id':str(user.id),'full_name':user.full_name,'email':user.email,'role':role}}
print(json.dumps(result))
"""
    sessions = json.loads(
        subprocess.check_output(
            [
                "docker",
                "exec",
                PROJECT + "-backend-1",
                "python",
                "-c",
                code,
            ],
            text=True,
            encoding="utf-8",
        )
    )
    base = "http://127.0.0.1:14211"
    routes = {
        "admin": [
            "dashboard",
            "usuarios",
            "estudiantes",
            "grados-secciones",
            "cursos",
            "importacion",
        ],
        "teacher": ["dashboard", "cursos", "calificaciones", "asistencia", "importacion"],
        "coordinator": ["dashboard", "seguimiento", "analitica", "ia", "reportes"],
    }
    checks, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            headless=True,
        )
        for role, paths in routes.items():
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            session = sessions[role]
            context.add_init_script(
                "localStorage.setItem('paideia_access_token',"
                + json.dumps(session["access_token"])
                + ");localStorage.setItem('paideia_user',"
                + json.dumps(json.dumps(session["user"]))
                + ");"
            )
            context.route(
                "**/*",
                lambda r: r.continue_() if r.request.url.startswith(base + "/") else r.abort(),
            )
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            for path in paths:
                page.goto(base + "/" + path)
                page.wait_for_load_state("networkidle")
                assert page.url == base + "/" + path
                expect(page.locator("aside.data-notice")).to_have_count(0)
                assert_presentation(page)
                assert page.locator("h1").count() > 0
                radii = page.locator(
                    "main select, main input:not([type=checkbox]):not([type=radio])"
                ).evaluate_all(
                    "els => els.filter(e => e.getBoundingClientRect().width)"
                    ".map(e => getComputedStyle(e).borderRadius)"
                )
                assert all(value == "7px" for value in radii), (role, path, radii)
                page.screenshot(
                    path=str(CONFIG.parent / f"history-{role}-{path}.png"), full_page=True
                )
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
                    role,
                    path,
                )
                page.set_viewport_size({"width": 1280, "height": 900})
                checks.append(role + "/" + path)
            headers = {"Authorization": "Bearer " + session["access_token"]}
            if role == "teacher":
                catalog = context.request.get(
                    base + "/api/v1/academic/catalog", headers=headers
                ).json()
                grade = catalog["grades"][0]
                section = next(s for s in catalog["sections"] if s["grade_id"] == grade["id"])
                course = next(c for c in catalog["courses"] if c["name"] == "Computación")
                page.goto(base + "/calificaciones")
                page.get_by_label(re.compile("^Nivel")).select_option(grade["level"])
                page.get_by_label(re.compile("^Grado")).select_option(grade["id"])
                page.get_by_label(re.compile("^Sección")).select_option(section["id"])
                page.get_by_label(re.compile("^Curso")).select_option(course["id"])
                page.get_by_label("Periodo académico", exact=True).select_option(
                    catalog["periods"][-1]["id"]
                )
                expect(page.get_by_text("Notas por mes", exact=True)).to_be_visible()
                page.get_by_text("Notas por mes", exact=True).click()
                option = (
                    page.locator('select[aria-label="Evaluación guardada"] option')
                    .filter(has_text="agosto")
                    .first
                )
                expect(option).to_have_count(1)
                page.get_by_label("Evaluación guardada", exact=True).select_option(
                    option.get_attribute("value")
                )
                page.wait_for_load_state("networkidle")
                values = page.locator("input[type=number]").evaluate_all(
                    "els => els.filter(e => e.getBoundingClientRect().width).map(e => e.value)"
                )
                assert values and all(v != "" for v in values)
                assert_presentation(page)
                page.screenshot(
                    path=str(CONFIG.parent / "history-populated-grades.png"), full_page=True
                )
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                checks.append("populated_monthly_grade_matrix")
            if role == "coordinator":
                api = context.request
                catalog = api.get(base + "/api/v1/academic/catalog", headers=headers).json()
                assert len(catalog["sections"]) == 8
                status = api.get(base + "/api/v1/academic/data-status", headers=headers).json()
                assert status["origins"] == {"recorded": 10, "excel": 1049, "synthetic": 4788}
                period = catalog["periods"][-1]
                assert period["bimester_months"] == {
                    "3": 1, "4": 1, "5": 2, "6": 2, "7": 2, "8": 3, "9": 3
                }
                for month in range(3, 10):
                    report = api.get(
                        base + "/api/v1/reports/students",
                        headers=headers,
                        params={"period_id": period["id"], "month": month},
                    ).json()
                    assert len(report) == 139 and all(r["grade_count"] for r in report)
                page.goto(base + "/reportes")
                page.wait_for_load_state("networkidle")
                expect(page.locator("input[type=month]")).to_have_value("2026-09")
                selected_grade = catalog["grades"][0]
                exported = api.get(
                    base + "/api/v1/reports/export.xlsx", headers=headers,
                    params={"grade_id": selected_grade["id"], "period_id": period["id"], "month": 9},
                )
                assert exported.status == 200
                with ZipFile(BytesIO(exported.body())) as workbook:
                    sheet_xml = workbook.read("xl/worksheets/sheet1.xml")
                    assert b"average_score" in sheet_xml
                    assert b"synthetic_count" not in sheet_xml
                page.get_by_label(re.compile("^Nivel")).select_option(selected_grade["level"])
                page.get_by_label(re.compile("^Grado")).select_option(selected_grade["id"])
                expect(page.get_by_role("button", name="Ver ficha").first).to_be_visible()
                page.get_by_role("button", name="Ver ficha").first.click()
                expect(page.get_by_role("heading", name="Reporte individual")).to_be_visible()
                expect(page.locator(".individual .origin-badge")).to_have_count(0)
                assert_presentation(page)
                page.emulate_media(media="print")
                assert_presentation(page)
                page.emulate_media(media="screen")
                page.screenshot(
                    path=str(CONFIG.parent / "history-populated-report.png"), full_page=True
                )
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                page.set_viewport_size({"width": 1280, "height": 900})
                page.goto(base + "/ia")
                page.get_by_label(re.compile("^Grado")).select_option(catalog["grades"][0]["id"])
                section = next(
                    s for s in catalog["sections"] if s["grade_id"] == catalog["grades"][0]["id"]
                )
                page.get_by_label(re.compile("^Aula")).select_option(section["id"])
                page.get_by_label(re.compile("^Predecir")).select_option("bimester")
                page.get_by_label("Último bimestre completado").fill("3")
                page.get_by_role("button", name="Analizar rendimiento").click()
                expect(page.get_by_label("Resumen del análisis")).to_be_visible()
                assert page.locator(".estimate").count() > 0
                assert_presentation(page)
                page.screenshot(
                    path=str(CONFIG.parent / "history-forecast-populated.png"), full_page=True
                )
                checks.append("populated_bimester_forecast")
            context.close()
        anonymous = browser.new_context(viewport={"width": 390, "height": 844})
        login = anonymous.new_page()
        login.goto(base + "/login")
        expect(login.get_by_role("button", name="Iniciar sesión")).to_be_visible()
        assert login.locator("input").evaluate_all("els => els.every(e => getComputedStyle(e).borderRadius === '7px')")
        assert login.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        checks.append("login_mobile")
        anonymous.close()
        browser.close()
    assert not errors, errors
    (CONFIG.parent / "loaded-history-ui.result.json").write_text(
        json.dumps(
            {
                "passed": True,
                "checks": checks,
                "javascript_errors": errors,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Loaded history and all staff views passed")


if __name__ == "__main__":
    main()
