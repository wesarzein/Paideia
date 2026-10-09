"""Essential single-page UI journey; preserves existing lab records and private evidence.

Run with the private Playwright venv. --stage resumes a specific step without resetting
the lab. Uses a dedicated synthetic course in the existing authorized PostgreSQL.
"""

import argparse
import base64
import ctypes
import json
import re
import subprocess
import traceback

from playwright.sync_api import expect, sync_playwright
from verify_academic_lab_api import CONFIG, PROJECT, digest, guard_host

STATE = CONFIG.parent / "academic-ui.state.json"


def free_memory():
    class Memory(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong)
            for name in (
                "total",
                "available",
                "page_total",
                "page_available",
                "virtual_total",
                "virtual_available",
                "extended",
            )
        ]

    memory = Memory()
    memory.length = ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise RuntimeError("Cannot verify available memory")
    return memory.available


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", choices=["all", "editor", "import", "manual", "history"], default="all"
    )
    parser.add_argument(
        "--browser", default="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
    )
    args = parser.parse_args()
    guard_host()
    assert free_memory() >= 1536 * 1024**2, "Insufficient memory for the browser journey"
    config = dict(
        line.split("=", 1)
        for line in CONFIG.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line and not line.startswith("#")
    )
    base = f"http://127.0.0.1:{config['FRONTEND_PORT']}"
    assert base == "http://127.0.0.1:14211"
    code = (
        "import base64,sys; sys.path.insert(0,'tests/unit'); "
        "from institutional_fixture import workbook_bytes; "
        "print(base64.b64encode(workbook_bytes(changes={'C7':25,'A7':'EXTERNO'})).decode())"
    )
    fixture = CONFIG.parent / "phase4b3.synthetic.xlsx"
    fixture.write_bytes(
        base64.b64decode(
            subprocess.check_output(
                ["docker", "exec", PROJECT + "-backend-1", "python", "-B", "-c", code]
            )
        )
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True)
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

        def api(method, path, payload=None, status=200):
            response = context.request.fetch(
                base + "/api/v1" + path, method=method, headers=headers, data=payload
            )
            assert response.status == status, (path, response.status)
            return response.json()

        state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None
        catalog = api("GET", "/academic/catalog")
        student = next(s for s in api("GET", "/students") if s["student_code"] == "1SA001")
        period = catalog["periods"][0]
        if state is None:
            baseline = api("GET", "/grades")
            assert len(baseline) == 21, "Expected the preserved initial lab inventory"
            guard_host()
            course = api(
                "POST",
                "/courses",
                {"name": "Validación visual sintética", "code": "SYN-UI-4B"},
                201,
            )
            api(
                "POST",
                f"/courses/{course['id']}/assignments",
                {"section_id": student["section_id"]},
                201,
            )
            state = {"course": course, "baseline": baseline, "checks": []}
            STATE.write_text(json.dumps(state), encoding="utf-8")
        course = state["course"]
        scope = f"/courses/{course['id']}"

        def preserved():
            rows = api("GET", "/grades")
            original_ids = {row["id"] for row in state["baseline"]}
            original = [row for row in rows if row["id"] in original_ids]
            assert sorted(original, key=lambda r: r["id"]) == sorted(
                state["baseline"], key=lambda r: r["id"]
            )
            return rows

        def passed(check):
            preserved()
            assert not errors, "Browser JavaScript errors"
            if check not in state["checks"]:
                state["checks"].append(check)
            STATE.write_text(json.dumps(state), encoding="utf-8")
            print(json.dumps({"check": check, "passed": True}), flush=True)

        def editor():
            page.goto(base + "/cursos")
            page.locator("tbody tr").filter(has_text="SYN-UI-4B").get_by_role(
                "button", name="Configurar curso", exact=True
            ).click()
            panel = page.locator("app-evaluation-configurator")
            expect(panel.locator(".version")).to_be_visible()
            return panel

        if args.stage in ("all", "editor") and "editor" not in state["checks"]:
            panel = editor()
            assert (
                api("GET", scope + "/evaluation-configurations/current?period_id=" + period["id"])[
                    "version"
                ]
                == 0
            ), "Resume the next stage after a completed publication"
            panel.get_by_role("button", name="Agregar competencia").click()
            panel.get_by_label("Nombre de competencia").last.fill("Competencia sintética visual")
            block = panel.locator("fieldset").nth(1)
            expect(block.locator("legend")).to_contain_text("Mes 1")
            first = block.locator(".criterion-row").first
            first.locator("select").select_option(index=1)
            first.get_by_label("Peso", exact=True).fill("3")
            first.locator(".order button").nth(1).click()
            block.locator(".criterion-row").nth(1).locator(".order button").nth(0).click()
            panel.get_by_role("button", name="Agregar criterio", exact=True).first.click()
            extra = block.locator(".criterion-row").last
            extra.get_by_label("Nombre del criterio").fill("Criterio sintético visual")
            extra.get_by_label("Opcional", exact=True).check()
            extra.get_by_label("Activo", exact=True).uncheck()
            panel.locator("textarea").first.fill(
                "ROUND(MEAN(b1_actitud,b1_cuaderno,b1_modulo,b1_exposicion,b1_evaluacion),1)"
            )
            for field in panel.locator(".scores input").all():
                field.fill("10")
            with page.expect_response(lambda r: "/evaluation-preview" in r.url) as reply:
                panel.get_by_role("button", name="Previsualizar resultados").click()
            preview_result = reply.value.json()
            (CONFIG.parent / "academic-ui.preview.json").write_text(
                json.dumps(preview_result), encoding="utf-8"
            )
            assert reply.value.status == 200
            assert all(value == 10 for value in preview_result["formula_results"].values())
            panel.get_by_label("Motivo del cambio").fill("Borrador visual sintético")
            with page.expect_response(lambda r: r.url.endswith("/drafts")) as reply:
                panel.get_by_role("button", name="Guardar borrador").click()
            assert reply.value.status == 201
            assert (
                api("GET", scope + "/evaluation-configurations/active?period_id=" + period["id"])[
                    "state"
                ]
                == "default"
            )
            panel.get_by_label("Motivo del cambio").fill("Publicación visual sintética")
            with page.expect_response(lambda r: r.url.endswith("/publish")) as reply:
                panel.get_by_role("button", name="Publicar versión").click()
            assert reply.value.status == 201
            state["published"] = reply.value.json()
            passed("editor")

        if args.stage in ("all", "import") and "import" not in state["checks"]:
            page.goto(base + "/importacion")
            page.get_by_role("button", name="Calificaciones", exact=True).click()
            page.get_by_label(re.compile(r"^Curso")).select_option(course["id"])
            page.get_by_label(re.compile(r"^Periodo")).select_option(period["id"])
            with page.expect_response(lambda r: "/imports/grades/preview" in r.url) as reply:
                page.locator('input[type="file"]').set_input_files(fixture)
            assert reply.value.status == 200 and reply.value.json()["total"] == 10
            confirm = page.get_by_role("button", name="Confirmar e importar calificaciones")
            expect(confirm).to_be_disabled()
            page.get_by_label("Año académico", exact=True).fill("2026")
            page.get_by_label("Bimestre", exact=True).fill("1")
            page.get_by_label("Grado institucional").select_option(student["grade_id"])
            page.get_by_label("Sección institucional").select_option(student["section_id"])
            for label, name, day in [
                ("1 MES", "Visual semana 4", "2026-04-01"),
                ("2 MES", "Visual semana 8", "2026-04-29"),
            ]:
                page.get_by_label("Evaluación " + label, exact=True).fill(name)
                page.get_by_label("Fecha " + label, exact=True).fill(day)
            page.get_by_label("Confirmo curso, periodo", exact=False).check()
            review = page.get_by_role("button", name="Revisar registros existentes")
            with page.expect_response(lambda r: "/imports/grades/review" in r.url) as reply:
                review.click()
            assert reply.value.status == 422
            for index in range(1, 11):
                page.get_by_label(f"Estudiante fila {index}", exact=True).select_option("1SA001")
            page.get_by_label("score fila 1", exact=True).fill("0")
            with page.expect_response(lambda r: "/imports/grades/review" in r.url) as reply:
                review.click()
            assert reply.value.status == 200
            with page.expect_response(lambda r: "/imports/grades/commit" in r.url) as reply:
                confirm.click()
            assert reply.value.json()["imported"] == 10
            with page.expect_response(lambda r: "/imports/grades/review" in r.url):
                review.click()
            with page.expect_response(lambda r: "/imports/grades/commit" in r.url) as reply:
                confirm.click()
            assert reply.value.json()["skipped"] == 10
            state["imported"] = [r for r in preserved() if r["course_id"] == course["id"]]
            assert len(state["imported"]) == 10
            assert all(
                r["evaluation_revision_id"] == state["published"]["id"] for r in state["imported"]
            )
            passed("import")

        if args.stage in ("all", "manual") and "manual" not in state["checks"]:
            page.goto(base + "/calificaciones")
            page.get_by_label(re.compile(r"^Nivel")).select_option("Secundaria")
            page.get_by_label(re.compile(r"^Grado")).select_option(student["grade_id"])
            page.get_by_label(re.compile(r"^Sección")).select_option(student["section_id"])
            page.get_by_label(re.compile(r"^Curso")).select_option(course["id"])
            page.get_by_label(re.compile(r"^Periodo")).select_option(period["id"])
            page.get_by_label("Bimestre institucional", exact=True).fill("1")
            page.get_by_label("Bloque de evaluación", exact=True).select_option(index=1)
            page.get_by_label("Nombre de evaluación", exact=True).fill("Manual visual explícita")
            page.get_by_label("Fecha de evaluación", exact=True).fill("2026-04-29")
            expect(page.get_by_label("Nota de criterio").first).to_be_visible()
            page.get_by_label("Nota de criterio").first.fill("14")
            with page.expect_response(
                lambda r: r.url.endswith("/grades") and r.request.method == "POST"
            ) as reply:
                page.get_by_role("button", name="Guardar matriz").click()
            assert reply.value.status == 201
            state["manual"] = reply.value.json()
            assert state["manual"]["academic_bimester"] == 1
            assert state["manual"]["evaluation_block"] == 2
            assert state["manual"]["evaluation_revision_id"] == state["published"]["id"]
            page.get_by_label("Mes de consulta", exact=True).fill("2026-04")
            expect(page.locator("section.table-wrap").last.locator("tbody tr")).to_have_count(11)
            page.reload()
            preserved()
            passed("manual")

        if args.stage in ("all", "history") and "history" not in state["checks"]:
            panel = editor()
            panel.locator(".criterion-row").first.get_by_label("Peso", exact=True).fill("9")
            panel.get_by_label("Motivo del cambio").fill("Versión posterior visual")
            with page.expect_response(lambda r: r.url.endswith("/publish")) as reply:
                panel.get_by_role("button", name="Publicar versión").click()
            assert reply.value.status == 201
            panel.get_by_label("Motivo del cambio").fill("Restauración visual sintética")
            panel.get_by_role("button", name="Restablecer plantilla institucional").click()
            with page.expect_response(lambda r: r.url.endswith("/restore-institutional")) as reply:
                page.get_by_role("button", name="Confirmar", exact=True).click()
            assert reply.value.status == 201
            panel.locator("summary").click()
            expect(panel.locator(".history-item")).to_have_count(4)
            panel.locator(".history-item").last.click()
            expect(panel.get_by_role("status")).to_contain_text("cargada para revisión")
            rows = preserved()
            expected = {r["id"]: r for r in state["imported"] + [state["manual"]]}
            assert {r["id"]: r for r in rows if r["id"] in expected} == expected
            page.set_viewport_size({"width": 390, "height": 844})
            expect(panel.get_by_role("heading", name="Evaluación configurable")).to_be_visible()
            passed("history")
        final = preserved()
        print(
            json.dumps(
                {
                    "checks": state["checks"],
                    "preserved_initial_records": 21,
                    "grades_sha256": digest(final),
                    "javascript_errors": len(errors),
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        lines = [
            f.lineno
            for f in traceback.extract_tb(error.__traceback__)
            if f.filename.endswith("verify_academic_ui.py")
        ]
        print(
            json.dumps(
                {
                    "passed": False,
                    "error_type": type(error).__name__,
                    "script_line": lines[-1] if lines else None,
                }
            ),
            flush=True,
        )
        raise SystemExit(1) from None
