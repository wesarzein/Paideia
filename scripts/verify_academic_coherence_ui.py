"""Read-only imported grade, session identity and attendance UX verification."""

import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from verify_academic_lab_api import CONFIG, guard_host


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cdp', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    guard_host()
    config = dict(line.split('=', 1) for line in CONFIG.read_text(encoding='utf-8-sig').splitlines() if '=' in line and not line.startswith('#'))
    base = 'http://paideia-dev-phase4b3ui-frontend-1:4200'
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        context = browser.new_context(viewport={'width': 1600, 'height': 1000})
        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base + '/') else route.abort())
        page = context.new_page()
        page.set_default_timeout(12000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base + '/login')
        page.locator('input[name=email]').fill(config['INITIAL_ADMIN_EMAIL'])
        page.locator('input[name=password]').fill(config['INITIAL_ADMIN_PASSWORD'])
        page.get_by_role('button', name='Iniciar sesión').click()
        expect(page).not_to_have_url(base + '/login')
        user_name = page.evaluate("JSON.parse(localStorage.getItem('paideia_user')).full_name")
        expect(page.locator('.identity strong')).to_have_text(user_name)
        expect(page.locator('.identity small')).to_have_text('Administrador')

        def api(path):
            result = page.evaluate("""async path => {
              const response = await fetch('/api/v1' + path, {headers: {Authorization: 'Bearer ' + localStorage.getItem('paideia_access_token')}});
              return {status: response.status, data: await response.json()};
            }""", path)
            assert result['status'] == 200, (path, result['status'])
            return result['data']

        pupil = next(row for row in api('/students') if row['student_code'] == '1SA001')
        before = api('/grades')
        attendance_before = api('/attendance')
        page.goto(base + '/calificaciones')
        page.get_by_label(re.compile('^Nivel')).select_option('Secundaria')
        page.get_by_label(re.compile('^Grado')).select_option(pupil['grade_id'])
        page.get_by_label(re.compile('^Sección')).select_option(pupil['section_id'])
        page.get_by_label(re.compile('^Curso')).select_option(label='Computación')
        page.get_by_label('Periodo académico', exact=True).select_option(label='Año escolar 2026')
        course_id = page.get_by_label(re.compile('^Curso')).input_value()
        period_id = page.get_by_label('Periodo académico', exact=True).input_value()
        expected_records = [row for row in before if row['course_id'] == course_id and row['period_id'] == period_id]
        evaluation_count = len({(row['evaluation_name'], row['assessment_date'], row['academic_bimester'], row['evaluation_block']) for row in expected_records})
        selector = page.get_by_label('Evaluación guardada', exact=True)
        expect(selector.locator('option')).to_have_count(evaluation_count + 1)
        expect(page.get_by_text(f'{len(expected_records)} notas guardadas en este periodo')).to_be_visible()
        cells = page.get_by_role('spinbutton', name='Nota de criterio', exact=True)
        expect(cells).to_have_count(80)
        assert all(cells.evaluate_all('cells => cells.map(cell => cell.value.length > 0)'))
        august = next(option for option in selector.locator('option').all() if 'Agosto' in option.inner_text())
        selector.select_option(august.get_attribute('value'))
        expect(cells).to_have_count(80)
        expect(cells.first).to_have_value('15')
        expect(page.get_by_label('Mes de consulta')).to_have_count(0)
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(args.output / 'grades-visible.png'), full_page=True)

        page.goto(base + '/asistencia')
        page.get_by_label('Fecha de asistencia', exact=True).fill('2026-08-10')
        page.get_by_label(re.compile('^Nivel')).select_option('Secundaria')
        page.get_by_label(re.compile('^Grado')).select_option(pupil['grade_id'])
        page.get_by_label(re.compile('^Sección')).select_option(pupil['section_id'])
        page.get_by_label(re.compile('^Curso')).select_option(label='Computación')
        page.get_by_label('Periodo académico', exact=True).select_option(label='Año escolar 2026')
        expect(page.locator('input[aria-label^="Observación de "]')).to_have_count(16)
        page.locator('input[aria-label^="Observación de "]').first.fill('Retiro con permiso a las 11:30')
        page.get_by_role('button', name='Día siguiente', exact=True).click()
        expect(page.get_by_label('Fecha de asistencia', exact=True)).to_have_value('2026-08-11')
        expect(page.locator('input[aria-label^="Observación de "]').first).to_have_value('')
        expect(page.get_by_role('button', name='Guardar asistencia del día', exact=True)).to_be_enabled()
        expect(page.get_by_role('button', name='Hoy', exact=True)).to_be_visible()
        if args.output:
            page.screenshot(path=str(args.output / 'attendance-day.png'), full_page=True)
        page.set_viewport_size({'width': 390, 'height': 844})
        expect(page.get_by_label('Fecha de asistencia', exact=True)).to_be_visible()
        expect(page.locator('.identity small')).to_have_text('Administrador')
        assert api('/grades') == before
        assert api('/attendance') == attendance_before
        assert not errors, errors
        context.close()
        browser.close()
        print(json.dumps({'grade_records_visible': len(expected_records), 'saved_evaluations': evaluation_count, 'matrix_score_cells': 80, 'identity_and_role': True, 'attendance_observations': 16, 'day_navigation': True, 'mobile': True, 'browser_errors': 0, 'writes': 0}))


if __name__ == '__main__':
    main()
