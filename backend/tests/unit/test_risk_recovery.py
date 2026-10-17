from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_academic_authorization import scenario, sessions
from test_risk_registry import client_for, queue

from app.models.risk_model import RiskModelEvent, RiskModelRun
from app.services.risk_registry import acquire_worker_lock, release_worker_lock

__all__ = ["scenario", "sessions"]


def test_0018_roundtrip_preserves_academic_history(scenario, sessions):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    with sessions() as db:
        if db.bind.dialect.name != "postgresql":
            pytest.skip("Migration acceptance requires PostgreSQL")
        assert db.scalar(text("SELECT current_schema()")).startswith("phase2_")
    command.downgrade(Config("alembic.ini"), "0017_academic_change_history")
    fingerprint = text(
        "SELECT md5(string_agg(row_to_json(h)::text, chr(10) ORDER BY id)) "
        "FROM academic_change_history h"
    )
    with sessions() as db:
        before = db.scalar(fingerprint)
        assert db.scalar(text("SELECT count(*) FROM grade_records")) == 5
    command.upgrade(Config("alembic.ini"), "0018_risk_worker_recovery")
    command.downgrade(Config("alembic.ini"), "0017_academic_change_history")
    command.upgrade(Config("alembic.ini"), "head")
    with sessions() as db:
        assert db.scalar(fingerprint) == before
        assert db.scalar(text("SELECT count(*) FROM grade_records")) == 5


def test_worker_persists_candidate_without_activation_and_keeps_failed_dataset(
    scenario, sessions, monkeypatch
):
    from app.ai_worker import execute
    from app.services import local_risk_model

    client = client_for(scenario)
    with sessions() as db:
        if db.bind.dialect.name != "postgresql":
            pytest.skip("PostgreSQL worker lease required")
    job = queue(client).json()
    execute(UUID(job["id"]))
    state = client.get("/risk-models").json()
    assert state["active_run_id"] is None and state["worker_active"] is False
    assert state["runs"][0]["status"] == "candidate"
    assert state["runs"][0]["split"]["student_overlap"] == 0

    def insufficient(*args):
        raise ValueError("Insufficient training data")

    monkeypatch.setattr(local_risk_model, "train_candidate", insufficient)
    second = queue(client).json()
    with pytest.raises(RuntimeError, match="dataset retained"):
        execute(UUID(second["id"]))
    state = client.get("/risk-models").json()
    assert state["runs"][0]["error_code"] == "insufficient_training_data"
    assert state["runs"][1]["status"] == "candidate"
    assert state["active_run_id"] is None and state["worker_active"] is False


def test_recover_interrupted_claim_preserves_data_and_allows_new_request(scenario, sessions):
    client = client_for(scenario)
    job = queue(client).json()
    with sessions() as db:
        if db.bind.dialect.name != "postgresql":
            pytest.skip("PostgreSQL worker lease required")
        run = db.get(RiskModelRun, UUID(job["id"]))
        run.status, run.worker_token = "running", uuid4()
        schema = run.dataset_schema
        db.commit()
    result = client.post(
        f"/risk-models/{job['id']}/recover",
        json={"reason": "Interrupted synthetic worker", "acknowledge_synthetic": True},
    )
    assert result.status_code == 200
    assert result.json()["status"] == "failed"
    assert result.json()["error_code"] == "interrupted_recovered_request_new_training"
    assert client.get("/risk-models").json()["active_run_id"] is None
    with sessions() as db:
        run = db.get(RiskModelRun, UUID(job["id"]))
        assert run.dataset_schema == schema and run.worker_token is None
        assert db.scalar(
            select(RiskModelEvent).where(RiskModelEvent.action == "training_recovered")
        )
    assert queue(client).status_code == 202


def test_recovery_cannot_interrupt_a_live_worker_and_lock_releases_on_disconnect(
    scenario, sessions
):
    client = client_for(scenario)
    job = queue(client).json()
    with sessions() as db:
        if db.bind.dialect.name != "postgresql":
            pytest.skip("PostgreSQL worker lease required")
        engine = db.bind
    connection = engine.connect()
    key = acquire_worker_lock(connection)
    assert key is not None
    try:
        assert client.get("/risk-models").json()["worker_active"] is True
        result = client.post(
            f"/risk-models/{job['id']}/recover",
            json={"reason": "Do not cancel live process", "acknowledge_synthetic": True},
        )
        assert result.status_code == 409
        assert queue(client).status_code == 409
    finally:
        # Simulate a killed process: physically close its PostgreSQL session.
        connection.invalidate()
        connection.close()
    assert client.get("/risk-models").json()["worker_active"] is False
    assert (
        client.post(
            f"/risk-models/{job['id']}/recover",
            json={"reason": "Confirmed process gone", "acknowledge_synthetic": True},
        ).status_code
        == 200
    )


def test_worker_lock_cannot_be_acquired_concurrently(sessions):
    with sessions() as db:
        if db.bind.dialect.name != "postgresql":
            pytest.skip("PostgreSQL worker lease required")
        engine = db.bind
    with engine.connect() as first, engine.connect() as second:
        key = acquire_worker_lock(first)
        assert key is not None and acquire_worker_lock(second) is None
        release_worker_lock(first, key)
        second_key = acquire_worker_lock(second)
        assert second_key is not None
        release_worker_lock(second, second_key)


def test_recovery_requires_admin_ack_and_pending_demonstration(scenario, sessions):
    client = client_for(scenario)
    job = queue(client).json()
    endpoint = f"/risk-models/{job['id']}/recover"
    assert (
        client.post(
            endpoint,
            json={"reason": "Recovery without acknowledgement", "acknowledge_synthetic": False},
        ).status_code
        == 422
    )
    client_for(scenario, "teacher")
    assert (
        client.post(
            endpoint, json={"reason": "Unauthorized recovery", "acknowledge_synthetic": True}
        ).status_code
        == 403
    )


def test_unavailable_active_artifact_returns_controlled_error(scenario, sessions):
    from test_risk_registry import evaluated_result

    client = client_for(scenario)
    job = queue(client).json()
    with sessions() as db:
        run = db.get(RiskModelRun, UUID(job["id"]))
        run.status, run.result = "candidate", evaluated_result()
        db.commit()
    assert (
        client.post(
            f"/risk-models/{job['id']}/approve",
            json={"reason": "Synthetic review only", "acknowledge_synthetic": True},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/risk-models/demonstration/activate",
            json={
                "run_id": job["id"],
                "expected_version": 0,
                "reason": "Synthetic activation only",
                "acknowledge_synthetic": True,
            },
        ).status_code
        == 200
    )
    # A dataset that is unavailable after restart must not become a 500 response.
    assert client.get("/risk-models/demonstration/predictions").status_code == 503
