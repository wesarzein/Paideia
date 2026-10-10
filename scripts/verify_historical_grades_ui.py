"""Read-only real Excel preview plus controlled native grading UI responses."""
import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from verify_academic_lab_api import CONFIG, guard_host


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cdp', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    guard_host()
    config = dict(line.split('=', 1) for line in CONFIG.read_text(encoding='utf-8-sig').splitlines()
                  if '=' in line and not line.startswith('#'))
    base = 'http://paideia-dev-phase4b3ui-frontend-1:4200'
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        context = browser.new_context(viewport={'width': 1500, 'height': 1000})
        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base + '/') else route.abort())
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_default_timeout(12000)
        page.goto(base + '/login')
        page.locator('input[name=email]').fill(config['INITIAL_ADMIN_EMAIL'])
        page.locator('input[name=password]').fill(config['INITIAL_ADMIN_PASSWORD'])
        page.get_by_role('button', name='Iniciar sesión').click()
        expect(page).not_to_have_url(base + '/login')

        def api(path):
            result = page.evaluate("""async path => {
              const r = await fetch('/api/v1' + path, {headers: {Authorization: 'Bearer ' + localStorage.getItem('paideia_access_token')}});
              return {status:r.status, data:await r.json()};
            }""", path)
            assert result['status'] == 200, (path, result['status'])
            return result['data']

        before = api('/grades')
        pupil = next(row for row in api('/students') if row['student_code'] == '1SA001')
        page.goto(base + '/importacion')
        page.get_by_role('button', name='Calificaciones', exact=True).click()
        page.get_by_label('Nivel', exact=True).select_option('Secundaria')
        page.get_by_label('Grado', exact=True).select_option(pupil['grade_id'])
        page.get_by_label('Sección', exact=True).select_option(pupil['section_id'])
        page.get_by_label('Curso', exact=True).select_option(label='Computación')
        page.get_by_label('Periodo académico', exact=True).select_option(label='Año escolar 2026')
        course_id = page.get_by_label('Curso', exact=True).input_value()
        period_id = page.get_by_label('Periodo académico', exact=True).input_value()
        page.get_by_label('Bimestre', exact=True).select_option(label='1.º bimestre')
        expect(page.locator('input[type=date]')).to_have_count(0)
        page.get_by_role('button', name='Continuar y cargar Excel').click()
        page.locator('input[type=file]').set_input_files('C:/Users/sanch/Downloads/REGISTRO DE NOTA 1EROA SEC.xlsx')
        expect(page.locator('.grade-sheet tbody tr')).to_have_count(16)
        expect(page.locator('.grade-sheet input[type=number]')).to_have_count(160)
        expect(page.locator('input[type=checkbox]')).to_have_count(0)
        page.get_by_role('button', name='Guardar calificaciones', exact=True).click()
        expect(page.get_by_role('dialog')).to_be_visible()
        expect(page.get_by_role('dialog')).to_contain_text('160 se crearán')
        page.get_by_role('button', name='Volver a revisar').click()
        page.screenshot(path=str(args.output / 'historical-import.png'), full_page=True)

        page.goto(base + '/cursos')
        page.get_by_role('row').filter(has_text='Computación').get_by_role('button', name='Configurar curso').click()
        expect(page.get_by_role('heading', name='Competencias y criterios de evaluación')).to_be_visible()
        expect(page.locator('textarea')).to_have_count(0)
        page.get_by_role('button', name='Agregar competencia', exact=True).click()
        page.get_by_label('Nombre de competencia').fill('Competencia de prueba visual')
        page.screenshot(path=str(args.output / 'course-configuration.png'), full_page=True)

        # Controlled published configuration: no institutional competencies are invented/saved.
        published = api(f'/courses/{course_id}/evaluation-configurations/active?period_id={period_id}')
        published.update(id='visual-revision', state='published', version=1)
        published['configuration']['competencies'] = [{'key':'visual', 'name':'Competencia de prueba visual', 'position':0, 'is_active':True}]
        for criterion in published['configuration']['criteria']:
            criterion['competency_key'] = 'visual'
        context.route('**/evaluation-configurations/active?*', lambda route: route.fulfill(json=published))
        page.evaluate("const user=JSON.parse(localStorage.getItem('paideia_user'));user.role='teacher';localStorage.setItem('paideia_user',JSON.stringify(user))")
        page.goto(base + '/calificaciones')
        page.get_by_label(re.compile('^Nivel')).select_option('Secundaria')
        page.get_by_label(re.compile('^Grado')).select_option(pupil['grade_id'])
        page.get_by_label(re.compile('^Sección')).select_option(pupil['section_id'])
        page.get_by_label(re.compile('^Curso')).select_option(label='Computación')
        page.get_by_label('Periodo académico', exact=True).select_option(period_id)
        page.get_by_role('button', name='Nueva evaluación').click()
        page.get_by_label('Bimestre', exact=True).fill('4')
        page.get_by_label('Nombre de evaluación', exact=True).fill('Examen de hoy')
        page.get_by_label('Fecha de evaluación', exact=True).fill('2026-10-10')
        cells = page.locator('input[aria-label*=" · Actitud ante el área"]')
        expect(cells).to_have_count(16)
        cells.first.fill('18')
        page.locator('input[aria-label*=" · Cuaderno"]').first.fill('12')
        expect(page.locator('.course-competencies')).to_contain_text('Competencia de prueba visual')
        expect(page.locator('section.table-wrap table').first.locator('thead')).to_contain_text('Competencia de prueba visual')
        page.screenshot(path=str(args.output / 'native-evaluation.png'), full_page=True)
        # Verify native date and criterion payloads, with writes intercepted.
        writes = []
        def native_write(route):
            if route.request.method != 'POST':
                return route.continue_()
            payload = route.request.post_data_json
            writes.append(payload)
            route.fulfill(json={**payload, 'id':'visual-' + payload['evaluation_criterion_key'],
                'record_kind':'evaluation','assessment_weight':1, 'evaluation_revision_id':'visual-revision'})
        context.route('**/api/v1/grades', native_write)
        page.get_by_role('button', name='Guardar calificaciones', exact=True).click()
        expect(page.get_by_role('status').filter(has_text='2 de 2 notas guardadas')).to_be_visible()
        assert len(writes) == 2 and all(row['assessment_date'] == '2026-10-10' and row['academic_bimester'] == 4
                                       and row['evaluation_criterion_key'] for row in writes)
        page.goto(base + '/cursos')
        page.get_by_role('row').filter(has_text='Computación').get_by_role('button', name='Ver curso', exact=True).click()
        expect(page.get_by_role('heading', name='Competencia de prueba visual')).to_be_visible()
        expect(page.get_by_role('button', name='Publicar para los docentes')).to_have_count(0)
        expect(page.locator('textarea')).to_have_count(0)
        assert api('/grades') == before
        assert not errors, errors
        print(json.dumps({'real_excel_students':16,'real_excel_marks':160,'native_payloads_checked':len(writes),
                          'existing_grades_preserved':len(before),'javascript_errors':errors}))
        context.close()


if __name__ == '__main__':
    main()
