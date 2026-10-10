"""One reusable synthetic follow-up audits real API/UI; all 32 grades stay exact.

Recovery failures use controlled browser responses, never launch a training process.
"""

import json
import subprocess

from playwright.sync_api import expect, sync_playwright
from verify_academic_lab_api import CONFIG, PROJECT, digest, guard_host
from verify_academic_ui import free_memory


def main():
    guard_host()
    subprocess.run(['docker', 'exec', PROJECT + '-backend-1', 'python', '-B', '-c',
                    'from sqlalchemy import text; from app.core.database import engine; '
                    'c=engine.connect(); assert c.execute(text("SELECT current_database(),current_user,current_schema()")).one()=='
                    '("paideia_dev_phase4b3ui","paideia_dev","public"); '
                    'assert c.scalar(text("SELECT version_num FROM alembic_version"))=="0018_risk_worker_recovery"; c.close()'], check=True)
    assert free_memory() >= 1024 * 1024**2, "Insufficient memory for one read-only page"
    config = dict(
        line.split("=", 1)
        for line in CONFIG.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line and not line.startswith("#")
    )
    base = "http://127.0.0.1:14211"
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            headless=True,
        )
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.route(
            "**/*",
            lambda r: r.continue_()
            if r.request.url.startswith(base + "/")
            else r.abort(),
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "/login")
        page.locator('input[name="email"]').fill(config["INITIAL_ADMIN_EMAIL"])
        page.locator('input[name="password"]').fill(config["INITIAL_ADMIN_PASSWORD"])
        page.get_by_role("button", name="Iniciar sesión").click()
        expect(page).not_to_have_url(base + "/login")
        headers = {
            "Authorization": "Bearer "
            + page.evaluate("localStorage.getItem('paideia_access_token')")
        }

        def get(path):
            response = context.request.get(base + "/api/v1" + path, headers=headers)
            assert response.status == 200
            return response.json()

        before = get("/grades")
        assert len(before) == 32
        state_path = CONFIG.parent / 'stability-ui.state.json'
        fixture = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
        if not fixture:
            student = get('/students')[0]
            response = context.request.post(base + '/api/v1/follow-ups', headers=headers,
                                            data={'student_id': student['id'], 'action': 'Synthetic B3 history: initial observation', 'category': 'OBSERVATION'})
            assert response.status == 201
            fixture = {'follow_up_id': response.json()['id'], 'student': student}
            state_path.write_text(json.dumps(fixture), encoding='utf-8')
        followup = next(r for r in get('/follow-ups?student_id=' + fixture['student']['id']) if r['id'] == fixture['follow_up_id'])
        final_action = 'Synthetic B3 history: verified correction'
        if followup['action'] != final_action:
            response = context.request.patch(base + '/api/v1/follow-ups/' + fixture['follow_up_id'], headers=headers, data={'action': final_action})
            assert response.status == 200
        real_history = get('/academic/history?student_id=' + fixture['student']['id'])
        correction = next(r for r in real_history if r['record_id'] == fixture['follow_up_id'] and r['operation'] == 'UPDATE')
        assert correction['before']['action'] == 'Synthetic B3 history: initial observation'
        assert correction['after']['action'] == final_action
        assert correction['actor_role'] == 'admin' and correction['authorization']['method'] == 'PATCH'
        page.goto(base + "/estudiantes")
        with page.expect_response(lambda r: "/academic/history?" in r.url) as history:
            page.locator('tbody tr').filter(has_text=fixture['student']['student_code']).get_by_role('button', name='Ver ficha', exact=True).click()
        assert history.value.status == 200
        expect(
            page.get_by_role("heading", name="Historial de cambios académicos")
        ).to_be_visible()
        page.locator('app-academic-history article').filter(has_text='Corrección').get_by_text('Valores anteriores y posteriores').click()
        expect(page.locator('app-academic-history article').filter(has_text='Corrección').locator('pre').first).to_contain_text('initial observation')
        expect(page.locator('app-academic-history article').filter(has_text='Corrección').locator('pre').last).to_contain_text('verified correction')
        # Render before/after and failures through explicit controlled responses.
        # Database authorization and append-only behavior have separate PostgreSQL tests.
        sample = {
            "id": "synthetic",
            "entity": "grade_records",
            "record_id": "synthetic-record",
            "operation": "UPDATE",
            "actor_id": "synthetic-actor",
            "actor_role": "admin",
            "source": "authenticated_api",
            "created_at": "2026-10-09T12:00:00Z",
            "before": {"score": 12},
            "after": {"score": 0},
        }
        page.route("**/api/v1/academic/history?*", lambda r: r.fulfill(json=[sample]))
        page.get_by_role("button", name="Actualizar historial").click()
        page.get_by_text("Valores anteriores y posteriores").click()
        expect(page.locator("app-academic-history pre").first).to_contain_text("12")
        expect(page.locator("app-academic-history pre").last).to_contain_text("0")
        page.unroute("**/api/v1/academic/history?*")
        page.route(
            "**/api/v1/academic/history?*",
            lambda r: r.fulfill(
                status=403, json={"detail": "Controlled authorization denial"}
            ),
        )
        page.get_by_role("button", name="Actualizar historial").click()
        expect(page.locator('app-academic-history [role="alert"]')).to_contain_text(
            "autorizado"
        )
        state = get("/risk-models")
        assert state["worker_active"] is False
        sample_run = dict(
            state["runs"][0], id="synthetic-interrupted", status="running"
        )
        simulated = dict(state, runs=[sample_run] + state["runs"])
        page.route("**/api/v1/risk-models", lambda r: r.fulfill(json=simulated))
        page.goto(base + "/ia")
        recover = page.get_by_role("button", name="Recuperar solicitud interrumpida")
        expect(recover).to_be_disabled()
        page.locator('input[type="checkbox"]').check()
        page.get_by_label("Motivo").fill("Synthetic recovery review")
        expect(recover).to_be_enabled()
        page.route(
            "**/api/v1/risk-models/synthetic-interrupted/recover",
            lambda r: r.fulfill(status=409, json={"detail": "Proceso sigue activo"}),
        )
        recover.click()
        expect(page.get_by_role("alert")).to_contain_text("Proceso sigue activo")
        assert digest(get("/grades")) == digest(before)
        assert not errors, errors
        context.close()
        browser.close()
    result = {
        "passed": True,
        "grades": 32,
        "grades_sha256": digest(before),
        "history_read_and_before_after": "real API and browser with reusable synthetic follow-up",
        "zero_render_and_recovery_errors": "controlled UI responses",
    }
    (CONFIG.parent / "stability-ui.result.json").write_text(
        json.dumps(result), encoding="utf-8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
