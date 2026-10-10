"""Synthetic-only training/approval/inference browser journey; preserves 32 grades."""

import json
import subprocess
from time import perf_counter, sleep

from playwright.sync_api import expect, sync_playwright
from verify_academic_lab_api import CONFIG, PROJECT, digest, guard_host
from verify_academic_ui import free_memory


def main():
    guard_host()
    subprocess.run(
        [
            "docker",
            "exec",
            PROJECT + "-backend-1",
            "python",
            "-B",
            "-c",
            "from sqlalchemy.engine import make_url; from sqlalchemy import text; "
            "from app.core.config import settings; from app.core.database import engine; "
            "u=make_url(settings.database_url); assert (u.host,u.database,u.username)=="
            "('postgres','paideia_dev_phase4b3ui','paideia_dev'); c=engine.connect(); "
            "assert c.execute(text('SELECT current_database(),current_user,current_schema()')).one()=="
            "('paideia_dev_phase4b3ui','paideia_dev','public'); c.close()",
        ],
        check=True,
    )
    assert free_memory() >= 1536 * 1024**2, "Insufficient memory for browser/training"
    config = dict(
        line.split("=", 1)
        for line in CONFIG.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line and not line.startswith("#")
    )
    base = "http://127.0.0.1:14211"
    state_path = CONFIG.parent / "risk-ui.state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            headless=True,
        )
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.route(
            "**/*", lambda r: r.continue_() if r.request.url.startswith(base + "/") else r.abort()
        )
        page = context.new_page()
        page.set_default_timeout(15000)
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

        def api(path):
            response = context.request.get(base + "/api/v1" + path, headers=headers)
            assert response.status == 200, (path, response.status)
            return response.json()

        before = api("/grades")
        assert len(before) == 32
        page.goto(base + "/ia")
        expect(
            page.get_by_role("heading", name="DEMOSTRACIÓN · Datos completamente ficticios")
        ).to_be_visible()
        page.get_by_label("Reconozco que son datos ficticios", exact=False).check()
        page.get_by_placeholder("Revisión experimental de métricas y limitaciones").fill(
            "Revisión sintética de la segunda laptop, sin validez institucional"
        )
        if "run_id" not in state:
            with page.expect_response("**/api/v1/risk-models/demonstration/train") as response:
                page.get_by_role("button", name="Solicitar entrenamiento demostrativo").click()
            assert response.value.status == 202
            state["run_id"] = response.value.json()["id"]
            state_path.write_text(json.dumps(state), encoding="utf-8")
        run_id = state["run_id"]
        for _ in range(120):
            status = api("/risk-models")
            run = next(r for r in status["runs"] if r["id"] == run_id)
            if run["status"] not in {"queued", "running"}:
                break
            sleep(1)
        assert run["status"] in {"candidate", "approved"}, run["status"]
        page.get_by_role("button", name="Actualizar estado").click()
        if run["status"] == "candidate":
            page.get_by_role("button", name="Aprobar solo para demostración").click()
        if status["active_run_id"] != run_id:
            page.get_by_role("button", name="Activar / restaurar esta versión").click()
        expect(
            page.get_by_text("Modelo aprobado activo para demostración", exact=False)
        ).to_be_visible()
        start = perf_counter()
        with page.expect_response("**/api/v1/risk-models/demonstration/predictions") as response:
            page.get_by_role("button", name="Consultar demostración").click()
        predictions = response.value.json()
        elapsed = perf_counter() - start
        assert predictions["mode"] == "demonstration"
        assert any(r["prediction"]["status"] == "insufficient_history" for r in predictions["rows"])
        expect(page.get_by_text("Historia insuficiente", exact=True).first).to_be_visible()
        page.reload()
        expect(
            page.get_by_text("Modelo aprobado activo para demostración", exact=False)
        ).to_be_visible()
        page.get_by_label("Reconozco que son datos ficticios", exact=False).check()
        page.get_by_placeholder("Revisión experimental de métricas y limitaciones").fill(
            "Desactivación y restauración demostrativas verificadas"
        )
        page.get_by_role("button", name="Desactivar demostración").click()
        expect(page.get_by_text("Sin modelo activo", exact=False)).to_be_visible()
        page.get_by_role("button", name="Activar / restaurar esta versión").click()
        expect(
            page.get_by_text("Modelo aprobado activo para demostración", exact=False)
        ).to_be_visible()
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        after = api("/grades")
        assert digest(before) == digest(after)
        assert not errors, errors
        proof = {
            "passed": True,
            "run_id": run_id,
            "metrics": run["metrics"],
            "baseline": run["baseline"],
            "split": run["split"],
            "predictions": len(predictions["rows"]),
            "inference_seconds": elapsed,
            "grades_sha256": digest(after),
            "javascript_errors": len(errors),
        }
        (CONFIG.parent / "risk-ui.result.json").write_text(
            json.dumps(proof, indent=2), encoding="utf-8"
        )
        print(json.dumps(proof))
        browser.close()


if __name__ == "__main__":
    main()
