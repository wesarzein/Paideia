from copy import deepcopy
from uuid import UUID

import pytest
from sqlalchemy import select
from test_academic_authorization import scenario, sessions

from app.endpoints.risk_models import router
from app.models.risk_model import RiskModelEvent, RiskModelRun
from app.services.risk_features import FEATURE_NAMES

__all__ = ["scenario", "sessions"]


def client_for(scenario, role="admin"):
    client, _, actors, current = scenario
    current["user"] = actors[role]
    if not getattr(client.app.state, "risk_added", False):
        client.app.include_router(router, prefix="/risk-models")
        client.app.state.risk_added = True
    return client


def queue(client):
    return client.post("/risk-models/demonstration/train", json={"acknowledge_synthetic": True})


def evaluated_result():
    return {
        "artifact": {
            "schema_version": 1,
            "mode": "demonstration",
            "features": list(FEATURE_NAMES),
            "imputation": [0] * 7,
            "mean": [0] * 7,
            "scale": [1] * 7,
            "coefficients": [0] * 7,
            "intercept": 0,
        },
        "split": {"student_overlap": 0, "test_count": 24},
        "lineage": {"personal_data": False},
        "metrics": {"f1": 0.5},
    }


def test_queue_is_durable_and_cannot_launch_two_pending_jobs(scenario, monkeypatch, sessions):
    monkeypatch.delenv("PAIDEIA_AI_AUTORUN", raising=False)
    client = client_for(scenario)
    response = queue(client)
    assert response.status_code == 202
    assert queue(client).status_code == 409
    assert client.get("/risk-models").json()["active_run_id"] is None
    with sessions() as db:
        assert db.scalar(select(RiskModelRun)).status == "queued"
        assert db.scalar(select(RiskModelEvent)).action == "training_requested"


def test_institutional_mode_and_unordered_demo_thresholds_are_rejected(scenario):
    client = client_for(scenario)
    base = {"acknowledge_synthetic": True}
    assert (
        client.post(
            "/risk-models/demonstration/train", json={**base, "mode": "institutional"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/risk-models/demonstration/train",
            json={**base, "medium_probability": 0.8, "high_probability": 0.7},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/risk-models/demonstration/activate",
            json={**base, "reason": "     ", "expected_version": 0},
        ).status_code
        == 422
    )


@pytest.mark.parametrize("role", ["teacher", "coordinator", "director", "student", "parent"])
def test_non_admin_cannot_train_approve_or_deploy(scenario, role):
    client = client_for(scenario, role)
    assert queue(client).status_code == 403
    assert (
        client.post(
            "/risk-models/demonstration/activate",
            json={"expected_version": 0, "reason": "Unauthorized", "acknowledge_synthetic": True},
        ).status_code
        == 403
    )
    assert client.get("/risk-models/events").status_code == 403
    expected = 403 if role in {"director", "student", "parent"} else 200
    assert client.get("/risk-models").status_code == expected


def test_approval_activation_deactivation_and_stale_version(scenario, sessions, monkeypatch):
    monkeypatch.delenv("PAIDEIA_AI_AUTORUN", raising=False)
    client = client_for(scenario)
    run_id = queue(client).json()["id"]
    decision = {"reason": "Reviewed experimental metrics", "acknowledge_synthetic": True}
    assert client.post(f"/risk-models/{run_id}/approve", json=decision).status_code == 409
    with sessions() as db:
        run = db.get(RiskModelRun, UUID(run_id))
        run.status, run.result = "candidate", evaluated_result()
        db.commit()
    assert client.post(f"/risk-models/{run_id}/approve", json=decision).status_code == 200
    payload = {**decision, "run_id": run_id, "expected_version": 0}
    assert client.post("/risk-models/demonstration/activate", json=payload).status_code == 200
    assert client.post("/risk-models/demonstration/activate", json=payload).status_code == 409
    payload.update(run_id=None, expected_version=1)
    assert client.post("/risk-models/demonstration/activate", json=payload).status_code == 200
    payload.update(run_id=run_id, expected_version=2)
    assert client.post("/risk-models/demonstration/activate", json=payload).status_code == 200
    assert client.get("/risk-models").json()["deployment_version"] == 3
    events = client.get("/risk-models/events").json()
    assert len(events) == 5
    assert all(e["actor_id"] for e in events)
    assert client.get("/risk-models").json()["institutional_status"].startswith("inactive")


def test_invalid_artifact_cannot_be_approved(scenario, sessions, monkeypatch):
    monkeypatch.delenv("PAIDEIA_AI_AUTORUN", raising=False)
    client = client_for(scenario)
    run_id = queue(client).json()["id"]
    with sessions() as db:
        run = db.get(RiskModelRun, UUID(run_id))
        result = deepcopy(evaluated_result())
        result["artifact"]["scale"] = [0] * 7
        run.status, run.result = "candidate", result
        db.commit()
    response = client.post(
        f"/risk-models/{run_id}/approve",
        json={"reason": "Review invalid", "acknowledge_synthetic": True},
    )
    assert response.status_code == 409


def test_concurrent_activation_has_one_winner(scenario, sessions, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from fastapi import HTTPException

    from app.services.risk_registry import activate

    monkeypatch.delenv("PAIDEIA_AI_AUTORUN", raising=False)
    client = client_for(scenario)
    run_id = UUID(queue(client).json()["id"])
    with sessions() as db:
        if db.bind.dialect.name != "postgresql":
            pytest.skip("Requires PostgreSQL row locks")
        run = db.get(RiskModelRun, run_id)
        run.status, run.result = "candidate", evaluated_result()
        db.commit()
    assert (
        client.post(
            f"/risk-models/{run_id}/approve",
            json={"reason": "Concurrent demo review", "acknowledge_synthetic": True},
        ).status_code
        == 200
    )
    barrier = Barrier(2)

    def attempt():
        with sessions() as db:
            barrier.wait(timeout=10)
            try:
                activate(db, scenario[2]["admin"], run_id, 0, "Concurrent demonstration")
                return 200
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: attempt(), range(2))) == [200, 409]


@pytest.mark.parametrize("sessions", ["0015_user_account_status"], indirect=True)
def test_migration_roundtrip_preserves_prior_rows(sessions):
    import os
    from uuid import uuid4

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    if not os.environ.get("PAIDEIA_TEST_POSTGRES_URL"):
        pytest.skip("Requires PostgreSQL migrations in a UUID schema")
    with sessions() as db:
        student = uuid4()
        db.execute(
            text(
                "INSERT INTO students (id,first_name,last_name,status) "
                "VALUES (:id,'Fictional','Migration','ACTIVE')"
            ),
            {"id": student},
        )
        db.commit()
        before = db.execute(text("SELECT row_to_json(s) FROM students s")).all()
    command.upgrade(Config("alembic.ini"), "0016_local_risk_models")
    with sessions() as db:
        assert db.execute(text("SELECT row_to_json(s) FROM students s")).all() == before
        assert db.scalar(text("SELECT count(*) FROM risk_model_deployments")) == 2
    command.downgrade(Config("alembic.ini"), "0015_user_account_status")
    command.upgrade(Config("alembic.ini"), "0016_local_risk_models")
    with sessions() as db:
        assert db.execute(text("SELECT row_to_json(s) FROM students s")).all() == before
