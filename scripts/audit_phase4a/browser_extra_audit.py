"""Additional existing component and account UI capabilities; synthetic site only."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--browser", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    config = dict(
        line.split("=", 1)
        for line in (root / "config/local/phase4a.env").read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    assert (
        config["COMPOSE_PROJECT_NAME"] == "paideia-dev-phase4a"
        and config["FRONTEND_PORT"] == "14204"
    )
    results = []
    base = "http://localhost:14204"
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, headless=True)
        context = browser.new_context()
        context.route(
            "**/*", lambda r: r.continue_() if r.request.url.startswith(base + "/") else r.abort()
        )
        page = context.new_page()
        page.set_default_timeout(12000)
        page.goto(base + "/login")
        page.locator("[name=email]").fill(config["INITIAL_ADMIN_EMAIL"])
        page.locator("[name=password]").fill(config["INITIAL_ADMIN_PASSWORD"])
        page.get_by_role("button", name="Iniciar sesión").click()
        page.wait_for_url("**/dashboard")

        def result(identifier, expectation, observed, ok):
            results.append(
                dict(
                    id=identifier,
                    expected=expectation,
                    observed=observed,
                    status="verified" if ok else "defect",
                )
            )
            print(json.dumps(results[-1]), flush=True)

        page.goto(base + "/cursos")
        page.get_by_role("row").filter(has_text="Matemática").first.get_by_role(
            "button", name="Configurar curso", exact=True
        ).click()
        page.locator("[name=component_name]").fill("Criterio extra sintetico")
        page.locator("[name=component_weight]").fill("2")
        page.locator("[name=is_optional]").check()
        with page.expect_response(
            lambda r: r.request.method == "POST" and "/assessment-components" in r.url
        ) as reply:
            page.get_by_role("button", name="Agregar componente", exact=True).click()
        row = page.get_by_role("row").filter(has_text="Criterio extra sintetico").first
        expect(row).to_be_visible()
        result(
            "UI-EV-01",
            "Admin can add an optional custom course component from UI",
            reply.value.status,
            reply.value.status == 201,
        )
        row.locator("input.weight").fill("3")
        with page.expect_response(
            lambda r: r.request.method == "PATCH" and "/assessment-components/" in r.url
        ) as reply:
            row.get_by_role("button", name="Guardar peso", exact=True).click()
        expect(row.locator("input.weight")).to_have_value("3")
        result(
            "UI-EV-02",
            "Edited weight persists through API",
            reply.value.status,
            reply.value.status == 200,
        )
        page.reload()
        page.get_by_role("row").filter(has_text="Matemática").first.get_by_role(
            "button", name="Configurar curso", exact=True
        ).click()
        expect(
            page.get_by_role("row")
            .filter(has_text="Criterio extra sintetico")
            .first.locator("input.weight")
        ).to_have_value("3")
        result("UI-EV-03", "Component setting survives fresh page read", True, True)

        page.goto(base + "/usuarios")
        page.locator("[name=full_name]").fill("Docente extra sintetico")
        page.locator("[name=email]").fill("extra@phase4a.example.com")
        page.locator("[name=password]").fill("SyntheticExtraUser!2026")
        page.locator("[name=role_code]").select_option("teacher")
        with page.expect_response(
            lambda r: r.request.method == "POST" and r.url.endswith("/api/v1/users")
        ) as reply:
            page.locator("form button[type=submit]").click()
        expect(page.get_by_role("cell", name="Docente extra sintetico", exact=True)).to_be_visible()
        result(
            "UI-US-01",
            "Admin UI creates a teacher and rereads the saved account",
            reply.value.status,
            reply.value.status == 201,
        )
        browser.close()
    (args.private / "browser-extra-results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
