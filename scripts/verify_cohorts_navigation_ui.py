"""Read-only admin navigation/form checks; API persistence uses UUID test schemas."""

import argparse
import json

from playwright.sync_api import expect, sync_playwright
from verify_academic_lab_api import CONFIG, guard_host


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdp", required=True)
    args = parser.parse_args()
    guard_host()
    config = dict(
        line.split("=", 1)
        for line in CONFIG.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line and not line.startswith("#")
    )
    base = "http://paideia-dev-phase4b3ui-frontend-1:4200"
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        context.route(
            "**/*",
            lambda route: route.continue_()
            if route.request.url.startswith(base + "/")
            else route.abort(),
        )
        page = context.new_page()
        page.set_default_timeout(10000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base + "/login")
        page.locator("input[name=email]").fill(config["INITIAL_ADMIN_EMAIL"])
        page.locator("input[name=password]").fill(config["INITIAL_ADMIN_PASSWORD"])
        page.get_by_role("button", name="Iniciar sesión").click()
        expect(page).not_to_have_url(base + "/login")
        page.get_by_role("link", name="Grados y secciones", exact=True).click()
        expect(page).to_have_url(base + "/grados-secciones")
        expect(
            page.get_by_role("button", name="Crear grado", exact=True)
        ).to_be_visible()
        expect(
            page.get_by_role("button", name="Crear sección", exact=True)
        ).to_be_visible()
        level = page.locator("select[name=grade_level]")
        expect(level.locator("option")).to_have_text(["Primaria", "Secundaria"])
        page.locator("input[name=grade_name]").fill("2° grado")
        level.select_option("Secundaria")
        expect(level).to_have_value("Secundaria")
        expect(
            page.locator("select[name=section_grade] option").nth(1)
        ).to_be_attached()
        page.locator("select[name=section_grade]").select_option(index=1)
        page.locator("input[name=section_name]").fill("B")
        # UI role restrictions, independent of server permission tests.
        page.evaluate(
            "const user = JSON.parse(localStorage.getItem('paideia_user')); user.role = 'teacher'; localStorage.setItem('paideia_user', JSON.stringify(user));"
        )
        page.goto(base + "/dashboard")
        expect(
            page.get_by_role("link", name="Grados y secciones", exact=True)
        ).to_be_visible()
        page.goto(base + "/grados-secciones")
        expect(page).to_have_url(base + "/grados-secciones")
        expect(page.get_by_role("button", name="Crear grado", exact=True)).to_have_count(0)
        expect(page.get_by_role("button", name="Crear sección", exact=True)).to_have_count(0)
        page.goto(base + "/cursos")
        expect(page.get_by_role("button", name="Crear curso", exact=True)).to_have_count(0)
        expect(page.get_by_role("button", name="Editar curso", exact=True)).to_have_count(0)
        expect(page.get_by_role("button", name="Archivar curso", exact=True)).to_have_count(0)
        expect(page.get_by_role("button", name="Ver curso", exact=True).first).to_be_visible()
        page.goto(base + "/estudiantes")
        expect(page.get_by_role("button", name="Nuevo estudiante", exact=True)).to_have_count(0)
        page.goto(base + "/importacion")
        expect(page.get_by_role("button", name="Estudiantes", exact=True)).to_have_count(0)
        expect(page.get_by_role("button", name="Calificaciones", exact=True)).to_be_visible()
        assert not errors, errors
        context.close()
        browser.close()
        print(
            json.dumps(
                {
                    "admin_menu": True,
                    "visible_forms": 2,
                    "levels": 2,
                    "teacher_read_only": True,
                    "teacher_grades_import_only": True,
                    "ui_role_simulated": True,
                    "browser_errors": 0,
                    "commits": 0,
                }
            )
        )


if __name__ == "__main__":
    main()
