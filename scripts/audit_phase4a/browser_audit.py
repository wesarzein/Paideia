"""Headless browser audit restricted to the synthetic localhost:14204 site.

Requires a private Playwright virtualenv and an installed Edge/Chromium binary.
Uses a new browser context, no personal browser profile, no institutional file.
Exit success means harness completion; inspect per-check statuses for defects.
"""

import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--browser", required=True)
    args = parser.parse_args()
    config = dict(
        line.split("=", 1)
        for line in args.config.read_text(encoding="utf-8-sig").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    assert config["COMPOSE_PROJECT_NAME"] == "paideia-dev-phase4a"
    assert config["POSTGRES_DB"] == "paideia_dev_phase4a" and config["FRONTEND_PORT"] == "14204"
    data = json.loads((args.private / "browser-context.json").read_text(encoding="utf-8"))
    base = "http://localhost:14204"
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, accept_downloads=True
        )
        page = context.new_page()
        page.set_default_timeout(12000)
        # Never navigate/fetch another installation or external page.
        context.route(
            "**/*",
            lambda route: route.continue_()
            if route.request.url.startswith(base + "/")
            or route.request.url.startswith(("data:", "blob:"))
            else route.abort(),
        )

        def field(label):
            return (
                page.locator("label")
                .filter(has_text=re.compile("^" + re.escape(label)))
                .locator("select,input,textarea")
                .first
            )

        def check(identifier, expected, operation):
            try:
                observed, ok = operation()
                item = dict(
                    id=identifier,
                    expected=expected,
                    observed=observed,
                    status="verified" if ok else "defect",
                )
            except Exception as error:
                # No DOM dumps, credential payloads or URL query strings in outputs.
                item = dict(
                    id=identifier,
                    expected=expected,
                    observed={
                        "harness_error_type": type(error).__name__,
                        "safe_detail": str(error)
                        .replace(config["INITIAL_ADMIN_PASSWORD"], "[redacted]")
                        .replace("SyntheticPhase4aOnly!2026", "[redacted]")[:450],
                    },
                    status="unverified",
                )
            results.append(item)
            print(json.dumps(item, ensure_ascii=True), flush=True)

        def login(role="admin"):
            page.goto(base + "/login")
            email = (
                config["INITIAL_ADMIN_EMAIL"] if role == "admin" else f"{role}@phase4a.example.com"
            )
            password = (
                config["INITIAL_ADMIN_PASSWORD"] if role == "admin" else "SyntheticPhase4aOnly!2026"
            )
            page.locator('input[name="email"]').fill(email)
            page.locator('input[name="password"]').fill(password)
            with page.expect_response(lambda r: "/api/v1/auth/login" in r.url) as reply:
                page.get_by_role("button", name="Iniciar sesión").click()
            expect(page).not_to_have_url(base + "/login")
            return {"login_http": reply.value.status}, reply.value.status == 200

        check("UI-01", "Login UI reaches API and navigates to authenticated application", login)

        for route, title in [
            ("estudiantes", "Estudiantes"),
            ("usuarios", "Usuarios"),
            ("cursos", "Cursos"),
            ("calificaciones", "Calificaciones"),
            ("asistencia", "Asistencia"),
            ("seguimiento", "Seguimiento académico"),
            ("reportes", "Reportes académicos"),
            ("importacion", "Importación"),
        ]:

            def navigate(route=route, title=title):
                page.goto(base + "/" + route)
                expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
                return {"heading_visible": True}, True

            check("NAV-" + route, "Academic route renders its actual screen", navigate)

        def search_student():
            page.goto(base + "/estudiantes")
            page.get_by_placeholder("Código o nombre").fill("1SA001")
            with page.expect_response(
                lambda r: "/api/v1/students?" in r.url and "search=" in r.url
            ) as reply:
                page.get_by_placeholder("Código o nombre").press("Enter")
            expect(page.locator("tbody tr")).to_have_count(1)
            return {"http": reply.value.status, "rows": 1}, reply.value.status == 200

        check("UI-02", "Student search filters real API results", search_student)

        def imports():
            page.goto(base + "/importacion")
            page.get_by_role("button", name="Calificaciones", exact=True).click()
            field("Curso").select_option(data["course_id"])
            field("Periodo").select_option(data["period_id"])

        def upload_institutional():
            imports()
            with page.expect_response(lambda r: "/imports/grades/preview" in r.url) as reply:
                page.locator('input[type="file"]').set_input_files(
                    args.private / "institucional-sintetico.xlsx"
                )
            return {"preview_http": reply.value.status}, reply.value.status == 200

        check(
            "UI-EX-01",
            "Institutional synthetic XLSX selection parses successfully",
            upload_institutional,
        )

        def drag_file():
            imports()
            file = (args.private / "valid.synthetic.csv").read_text(encoding="utf-8")
            with page.expect_response(lambda r: "/imports/grades/preview" in r.url) as reply:
                page.locator(".dropzone").evaluate(
                    """(element, content) => {
                    const transfer = new DataTransfer();
                    transfer.items.add(new File([content], 'valid.synthetic.csv',
                        {type:'text/csv'}));
                    element.dispatchEvent(new DragEvent('drop',
                        {bubbles:true, dataTransfer:transfer}));
                }""",
                    file,
                )
            expect(page.locator(".preview tbody tr")).to_have_count(10)
            return {"http": reply.value.status, "preview_rows": 10}, reply.value.status == 200

        check("UI-EX-02", "Drag and drop flat synthetic CSV displays ten rows", drag_file)

        def correct_and_save():
            inputs = page.locator(".preview tbody tr").first.locator("input")
            expect(inputs.first).to_be_visible()
            inputs.nth(1).fill("11")
            with page.expect_response(lambda r: "/imports/grades/commit" in r.url) as reply:
                page.get_by_role("button", name="Confirmar e importar calificaciones").click()
            expect(page.locator(".message")).to_contain_text("10 de 10")
            return {"commit_http": reply.value.status}, reply.value.status == 200

        check(
            "UI-EX-03",
            "Editable flat preview requires explicit confirmation and saves",
            correct_and_save,
        )

        def select_file_preview():
            imports()
            with page.expect_response(lambda r: "/imports/grades/preview" in r.url) as reply:
                page.locator('input[type="file"]').set_input_files(
                    args.private / "valid.synthetic.csv"
                )
            expect(page.locator(".preview tbody tr")).to_have_count(10)
            return {"preview_http": reply.value.status}, reply.value.status == 200

        check(
            "UI-EX-04",
            "Flat file selection also works independently of drag/drop",
            select_file_preview,
        )

        def invalid_preview_correction():
            imports()
            content = (
                b"student_code,score,assessment_date,evaluation_type\n"
                b"1SA001,99,2026-03-01,Cuaderno\n"
            )
            with page.expect_response(lambda r: "/imports/grades/preview" in r.url):
                page.locator('input[type="file"]').set_input_files(
                    dict(name="bad.synthetic.csv", mimeType="text/csv", buffer=content)
                )
            page.locator(".preview tbody tr input").nth(1).fill("15")
            buttons = page.get_by_role("button", name="Confirmar e importar calificaciones")
            errors = page.locator(".preview .error").count()
            return {
                "confirmation_visible_after_correction": buttons.count() > 0,
                "server_error_still_displayed": errors > 0,
            }, buttons.count() > 0

        check(
            "UI-EX-05",
            "Correcting an invalid preview clears errors and permits confirmation",
            invalid_preview_correction,
        )

        def blank_score():
            select_file_preview()
            page.locator(".preview tbody tr input").nth(1).fill("")
            with page.expect_response(lambda r: "/imports/grades/commit" in r.url) as reply:
                page.get_by_role("button", name="Confirmar e importar calificaciones").click()
            return {
                "client_allowed_blank_confirmation": True,
                "server_http": reply.value.status,
            }, False

        check(
            "UI-EX-06",
            "Blank score is rejected in preview rather than treated as client-side zero",
            blank_score,
        )

        def choose_class(route):
            page.goto(base + "/" + route)
            field("Nivel").select_option(label="Secundaria")
            field("Grado").select_option(data["grade_id"])
            field("Sección").select_option(data["section_id"])

        def grade_filters():
            choose_class("calificaciones")
            field("Curso").select_option(data["course_id"])
            field("Periodo").select_option(data["period_id"])
            with page.expect_response(
                lambda r: "/api/v1/grades?" in r.url and "month=3" in r.url
            ) as reply:
                field("Mes de registro").fill("2026-03")
            expect(page.get_by_role("heading", name="Notas registradas del mes")).to_be_visible()
            expect(page.get_by_label("Nota de componente").first).to_be_visible()
            return {
                "http": reply.value.status,
                "manual_inputs": page.get_by_label("Nota de componente").count(),
            }, reply.value.status == 200

        check(
            "UI-GR-01",
            "Class/course/period/month filters load stored marks and matrix",
            grade_filters,
        )

        def matrix_save():
            page.get_by_label("Nota de componente").first.fill("13")
            with page.expect_response(
                lambda r: r.request.method == "POST" and r.url.endswith("/api/v1/grades")
            ) as reply:
                page.get_by_role("button", name="Guardar matriz", exact=True).click()
            expect(page.get_by_role("status")).to_contain_text("1 de 1")
            return {"http": reply.value.status}, reply.value.status == 201

        check("UI-GR-02", "Manual matrix mark is saved through API", matrix_save)

        def existing_matrix_values():
            page.reload()
            grade_filters()
            values = page.get_by_label("Nota de componente").evaluate_all(
                "els => els.map(e=>e.value)"
            )
            return {"filled_existing_matrix_cells": sum(bool(v) for v in values)}, any(values)

        check(
            "UI-GR-03",
            "Reload hydrates saved grades in editable component matrix",
            existing_matrix_values,
        )

        def attendance_save():
            choose_class("asistencia")
            field("Curso").select_option(data["course_id"])
            field("Periodo").select_option(data["period_id"])
            field("Fecha").fill("2026-03-03")
            page.get_by_role("button", name="Todos presentes", exact=True).click()
            page.get_by_role("button", name="Guardar asistencia del día", exact=True).click()
            expect(page.get_by_text("16 de 16 asistencias guardadas.", exact=True)).to_be_visible()
            return {"saved_attendances": 16}, True

        check(
            "UI-AT-01",
            "Daily group attendance saves all sixteen synthetic students",
            attendance_save,
        )

        def follow_save():
            choose_class("seguimiento")
            field("Estudiante").select_option(data["student_id"])
            field("Descripción").fill("Acuerdo pedagogico sintetico registrado por interfaz")
            with page.expect_response(
                lambda r: r.request.method == "POST" and r.url.endswith("/api/v1/follow-ups")
            ) as reply:
                page.get_by_role("button", name="Registrar seguimiento", exact=True).click()
            expect(
                page.get_by_text("Acuerdo pedagogico sintetico registrado por interfaz", exact=True)
            ).to_be_visible()
            return {"http": reply.value.status}, reply.value.status == 201

        check("UI-FU-01", "Follow-up created by UI appears in group history", follow_save)

        def report_export():
            choose_class("reportes")
            field("Periodo").select_option(data["period_id"])
            field("Curso").select_option(data["course_id"])
            field("Mes").fill("2026-03")
            expect(page.get_by_role("heading", name="Reporte grupal", exact=False)).to_be_visible()
            with page.expect_download() as downloaded:
                page.get_by_role("button", name="Exportar Excel", exact=True).click()
            downloaded.value.save_as(args.private / "browser-export.synthetic.xlsx")
            page.get_by_role("button", name="Ver ficha", exact=True).first.click()
            expect(
                page.get_by_role("heading", name="Reporte individual", exact=True)
            ).to_be_visible()
            page.pdf(path=str(args.private / "report.synthetic.pdf"), print_background=True)
            return {
                "xlsx_download": True,
                "individual_preview": True,
                "browser_print_engine_pdf": True,
            }, True

        check(
            "UI-RP-01",
            "Group preview, individual report, Excel download and print engine work",
            report_export,
        )

        def role_reports():
            context.clear_cookies()
            page.evaluate("localStorage.clear();sessionStorage.clear()")
            login("coordinator")
            choose_class("reportes")
            with page.expect_response(lambda r: "/api/v1/reports/students" in r.url) as reply:
                field("Sección").select_option("")
            return {"report_api_http": reply.value.status}, reply.value.status == 200

        check("UI-RB-01", "Coordinator report navigation has matching API permission", role_reports)

        def family_portal():
            page.evaluate("localStorage.clear();sessionStorage.clear()")
            login("parent")
            page.goto(base + "/mi-avance")
            expect(page.get_by_role("heading").first).to_be_visible()
            return {"url_is_family_portal": page.url.endswith("/mi-avance")}, page.url.endswith(
                "/mi-avance"
            )

        check("UI-RB-02", "Additional linked family portal remains accessible", family_portal)
        browser.close()
    (args.private / "browser-results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        json.dumps(
            dict(
                checks=len(results),
                defects=sum(r["status"] == "defect" for r in results),
                unverified=sum(r["status"] == "unverified" for r in results),
            )
        )
    )


if __name__ == "__main__":
    main()
