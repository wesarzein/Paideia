"""Workbook UX check; commit is allowed only after proving all marks are identical."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from verify_academic_lab_api import CONFIG, guard_host


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--cdp", required=True)
    parser.add_argument("--screenshot", type=Path)
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
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
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
        page.goto(base + "/importacion")
        page.get_by_role("button", name="Calificaciones", exact=True).click()
        expect(page.locator('input[type=file]')).to_have_count(0)
        page.get_by_role('button', name='Continuar y cargar Excel').click()
        expect(page.get_by_role('alert')).to_contain_text('Selecciona')
        def api(path):
            result = page.evaluate("""async path => {
              const response = await fetch('/api/v1' + path, {headers: {
                Authorization: 'Bearer ' + localStorage.getItem('paideia_access_token')
              }});
              return {status: response.status, data: await response.json()};
            }""", path)
            assert result['status'] == 200, (path, result['status'])
            return result['data']
        before = api('/grades')
        pupil = next(item for item in api('/students') if item['student_code'] == '1SA001')
        page.get_by_label('Nivel', exact=True).select_option('Secundaria')
        page.get_by_label('Grado', exact=True).select_option(pupil['grade_id'])
        page.get_by_label('Sección', exact=True).select_option(pupil['section_id'])
        page.get_by_label('Curso', exact=True).select_option(label='Computación')
        page.get_by_label('Periodo académico', exact=True).select_option(label='Año escolar 2026')
        page.get_by_label('Bimestre', exact=True).select_option(label='3.º bimestre')
        page.get_by_label('Evaluación del primer bloque').fill('Agosto')
        page.get_by_label('Fecha del primer bloque').fill('2026-08-10')
        page.get_by_label('Evaluación del segundo bloque').fill('Septiembre')
        page.get_by_label('Fecha del segundo bloque').fill('2026-09-10')
        page.get_by_role('button', name='Continuar y cargar Excel').click()
        page.locator("input[type=file]").set_input_files(args.file)
        matrix = page.get_by_role("table", name="Registro de notas del Excel")
        expect(matrix.locator("tbody tr")).to_have_count(16)
        expect(matrix.locator("input[type=number]")).to_have_count(160)
        expect(page.locator('input[type=checkbox]')).to_have_count(0)
        expect(page.get_by_label('Año escolar', exact=True)).to_have_count(0)
        expect(matrix.locator('select')).to_have_count(0)
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(args.screenshot), full_page=True)
        first = matrix.locator("input[type=number]").first
        old_score = first.input_value()
        first.fill("21")
        page.get_by_role('button', name='Guardar calificaciones', exact=True).click()
        expect(page.get_by_role('alert')).to_contain_text('nota entre 0 y 20')
        first.fill(old_score)
        page.get_by_role('button', name='Guardar calificaciones', exact=True).click()
        dialog = page.get_by_role('dialog')
        expect(dialog).to_be_visible()
        # Never alter the user's inventory during the browser check.
        expect(dialog).to_contain_text('0 notas se actualizarán; 0 se crearán; 160 se conservarán')
        with page.expect_response(lambda response: '/imports/grades/commit' in response.url) as commit:
            page.get_by_role('button', name='Confirmar y guardar', exact=True).click()
        assert commit.value.status == 200, commit.value.status
        result = commit.value.json()
        assert result['imported'] == result['updated'] == 0 and result['skipped'] == 160, result
        expect(page.get_by_role('alert')).to_contain_text('Operación completada')
        assert api('/grades') == before, 'Grade inventory changed'
        page.set_viewport_size({'width': 390, 'height': 844})
        expect(page.get_by_role('button', name='Guardar calificaciones', exact=True)).to_be_visible()
        assert page.locator('.table-scroll').evaluate('el => el.clientWidth < el.scrollWidth')
        page.set_viewport_size({'width': 1600, 'height': 1000})
        page.get_by_role("button", name="Estudiantes", exact=True).click()
        page.get_by_role('button', name='Continuar y cargar Excel').click()
        page.locator("input[type=file]").set_input_files(args.file)
        expect(page.locator(".preview table tbody tr")).to_have_count(16)
        expect(
            page.get_by_role("button", name="Guardar alumnos")
        ).to_be_enabled()
        for field in ("first_name", "last_name"):
            inputs = page.locator(f'.preview input[aria-label^="{field} fila "]')
            expect(inputs).to_have_count(16)
            assert all(
                inputs.evaluate_all(
                    "inputs => inputs.map(input => input.value.trim().length > 0)"
                )
            )
        assert not errors, errors
        context.close()
        browser.close()
        print(
            json.dumps(
                {
                    "students": 16,
                    "score_cells": 160,
                    "checkboxes": 0,
                    "context_selected_before_file": True,
                    "roster_rows": 16,
                    "roster_ready": True,
                    "browser_errors": 0,
                    "identical_commit_skipped": 160,
                    "grade_inventory_unchanged": True,
                }
            )
        )


if __name__ == "__main__":
    main()
