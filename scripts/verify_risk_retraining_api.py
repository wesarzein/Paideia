"""New demo candidate never replaces active model; verify explicit switch and rollback."""

import json
import subprocess
from time import sleep

from playwright.sync_api import sync_playwright
from verify_academic_lab_api import CONFIG, PROJECT, digest, guard_host
from verify_academic_ui import free_memory


def main():
    guard_host()
    # No Edge here: one API driver plus the backend's shared 768 MiB hard cap.
    # Browser + training still require 1.5 GiB in verify_risk_model_ui.py.
    assert free_memory() >= 1024 * 1024**2, "Insufficient host RAM for API-only retraining"
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
    config = dict(
        line.split("=", 1)
        for line in CONFIG.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line and not line.startswith("#")
    )
    base = "http://127.0.0.1:14211/api/v1"
    path = CONFIG.parent / "risk-retraining.state.json"
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    with sync_playwright() as p:
        context = p.request.new_context(base_url=base)
        login = context.post(
            base + "/auth/login",
            data={
                "email": config["INITIAL_ADMIN_EMAIL"],
                "password": config["INITIAL_ADMIN_PASSWORD"],
            },
        )
        assert login.status == 200
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}

        def api(method, endpoint, payload=None, expected=200):
            response = context.fetch(
                base + endpoint, method=method, data=payload, headers=headers
            )
            assert response.status == expected, (endpoint, response.status)
            return response.json()

        before = api("GET", "/grades")
        assert len(before) == 32
        status = api("GET", "/risk-models")
        original = status["active_run_id"]
        assert original
        previous = next(r for r in status["runs"] if r["id"] == original)
        if "run_id" not in state:
            state["run_id"] = api(
                "POST",
                "/risk-models/demonstration/train",
                {
                    "seed": 43,
                    "pupils": 80,
                    "failure_cutoff": 10.4,
                    "acknowledge_synthetic": True,
                },
                expected=202,
            )["id"]
            path.write_text(json.dumps(state), encoding="utf-8")
        run_id = state["run_id"]
        assert run_id != original
        for _ in range(120):
            status = api("GET", "/risk-models")
            assert status["active_run_id"] == original
            run = next(r for r in status["runs"] if r["id"] == run_id)
            if run["status"] not in {"queued", "running"}:
                break
            sleep(1)
        assert run["status"] in {"candidate", "approved"}
        decision = {
            "reason": "Synthetic retraining and rollback evidence",
            "acknowledge_synthetic": True,
        }
        if run["status"] == "candidate":
            api("POST", f"/risk-models/{run_id}/approve", decision)
        api(
            "POST",
            "/risk-models/demonstration/activate",
            {
                **decision,
                "run_id": run_id,
                "expected_version": status["deployment_version"],
            },
        )
        new_status = api("GET", "/risk-models")
        assert new_status["active_run_id"] == run_id
        assert api("GET", "/risk-models/demonstration/predictions")["run_id"] == run_id
        api(
            "POST",
            "/risk-models/demonstration/activate",
            {
                **decision,
                "run_id": original,
                "expected_version": new_status["deployment_version"],
            },
        )
        final = api("GET", "/risk-models")
        assert final["active_run_id"] == original
        assert next(r for r in final["runs"] if r["id"] == original) == previous
        assert digest(api("GET", "/grades")) == digest(before)
        proof = {
            "passed": True,
            "previous_run_id": original,
            "candidate_run_id": run_id,
            "metrics": run["metrics"],
            "split": run["split"],
            "grades_sha256": digest(before),
        }
        (CONFIG.parent / "risk-retraining.result.json").write_text(
            json.dumps(proof, indent=2), encoding="utf-8"
        )
        print(json.dumps(proof))
        context.dispose()


if __name__ == "__main__":
    main()
