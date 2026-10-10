"""Read-only BI browser evidence; exact conservation of all 32 lab grades."""

import json
import re
from time import perf_counter

from playwright.sync_api import expect, sync_playwright
from verify_academic_lab_api import CONFIG, digest, guard_host
from verify_academic_ui import free_memory


def main():
    guard_host()
    assert free_memory() >= 1536 * 1024**2, "Insufficient memory for Edge"
    config = dict(line.split("=", 1) for line in CONFIG.read_text(
        encoding="utf-8-sig").splitlines() if "=" in line and not line.startswith("#"))
    base = "http://127.0.0.1:14211"
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.route("**/*", lambda r: r.continue_()
                      if r.request.url.startswith(base + "/") else r.abort())
        page = context.new_page()
        page.set_default_timeout(15000)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "/login")
        page.locator('input[name="email"]').fill(config["INITIAL_ADMIN_EMAIL"])
        page.locator('input[name="password"]').fill(config["INITIAL_ADMIN_PASSWORD"])
        page.get_by_role("button", name="Iniciar sesión").click()
        expect(page).not_to_have_url(base + "/login")
        headers = {"Authorization": "Bearer " + page.evaluate(
            "localStorage.getItem('paideia_access_token')")}

        def get(path):
            response = context.request.get(base + "/api/v1" + path, headers=headers)
            assert response.status == 200
            return response.json()

        before = get("/grades")
        assert len(before) == 32
        start = perf_counter()
        result = get("/kpis")
        elapsed = perf_counter() - start
        assert result["grade_count"] == 32
        assert sum(result["literal_distribution"].values()) == 32
        assert sum(result["numeric_distribution"].values()) == 32
        page.goto(base + "/analitica")
        expect(page.get_by_role("heading", name="Distribución literal de notas")).to_be_visible()
        expect(page.get_by_role("img", name="Promedios mensuales de cero a veinte")).to_be_visible()
        course = next(c for c in get("/courses") if c["code"] == "SYN-UI-4B")
        page.get_by_label(re.compile(r"^Curso")).select_option(course["id"])
        expect(page.get_by_text("Alcance: un solo curso", exact=False)).to_be_visible()
        empty_period = next(p for p in get("/academic/periods") if "2027" in p["name"])
        page.get_by_label(re.compile(r"^Periodo")).select_option(empty_period["id"])
        expect(page.get_by_text("Sin calificaciones para estos filtros.", exact=False)).to_be_visible()
        expect(page.get_by_text("No calculable", exact=True).first).to_be_visible()
        page.route("**/api/v1/kpis*", lambda r: r.abort())
        page.get_by_role("button", name="Actualizar", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("No se pudo consultar")
        page.unroute("**/api/v1/kpis*")
        page.get_by_role("button", name="Reintentar").click()
        expect(page.get_by_text("Sin calificaciones para estos filtros.", exact=False)).to_be_visible()
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), page.evaluate(
            "Array.from(document.querySelectorAll('*')).filter(e => e.getBoundingClientRect().width > innerWidth).map(e => [e.tagName,e.className,Math.round(e.getBoundingClientRect().width)]).slice(0,15)")
        after = get("/grades")
        assert digest(before) == digest(after)
        assert not errors, errors
        proof = {"passed": True, "grade_count": len(after), "grades_sha256": digest(after),
                 "kpis_seconds": elapsed, "javascript_errors": len(errors),
                 "checks": ["charts", "course_scope", "empty", "network_error_retry", "mobile"]}
        (CONFIG.parent / "business-ui.result.json").write_text(
            json.dumps(proof, indent=2), encoding="utf-8")
        print(json.dumps(proof))
        browser.close()


if __name__ == "__main__":
    main()
