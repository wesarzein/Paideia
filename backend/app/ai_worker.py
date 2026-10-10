"""One-off process: claim one queued demo run, train, persist candidate, exit.

No automatic activation, no real data extraction, no persistent worker service.
"""

import os
import sys
from datetime import UTC, datetime
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import base as _mapped_models  # noqa: F401 - register academic foreign keys
from app.models.risk_model import RiskModelRun
from app.services.risk_registry import acquire_worker_lock, demo_engine, release_worker_lock


def execute(run_id):
    control = create_engine(settings.database_url)
    try:
        with control.connect() as lease:
            key = acquire_worker_lock(lease)
            if key is None:
                raise RuntimeError("Another training worker is active")
            lease.commit()
            try:
                execute_claimed(run_id, control, lease)
            finally:
                release_worker_lock(lease, key)
                lease.commit()
    finally:
        control.dispose()


def execute_claimed(run_id, control, lease):
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    if sys.platform == "linux":
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (180, 180))
    source_url = settings.database_url
    token = uuid4()
    with Session(control) as db:
        run = db.scalar(select(RiskModelRun).where(RiskModelRun.id == run_id).with_for_update())
        if run is None or run.status != "queued" or run.mode != "demonstration":
            raise ValueError("No queued demonstration run")
        schema, config = run.dataset_schema, run.configuration
        isolated = demo_engine(source_url, schema)  # validates generated identifier
        run.status = "running"
        run.worker_token, run.started_at = token, datetime.now(UTC)
        db.commit()
    try:
        with control.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        settings.database_url = (
            make_url(source_url)
            .update_query_dict({"options": f"-csearch_path={schema}"})
            .render_as_string(hide_password=False)
        )
        command.upgrade(Config("alembic.ini"), "head")
        settings.database_url = source_url
        from app.services.demonstration_dataset import labeled_examples, populate_demonstration
        from app.services.local_risk_model import train_candidate

        with Session(isolated) as db:
            lineage = populate_demonstration(db, config["seed"], config["pupils"])
            examples = labeled_examples(db, config["failure_cutoff"])
        result = train_candidate(examples, config["seed"])
        result["lineage"] = lineage
        result["artifact"]["failure_cutoff"] = config["failure_cutoff"]
        result["artifact"]["medium_probability"] = config["medium_probability"]
        result["artifact"]["high_probability"] = config["high_probability"]
        # A PostgreSQL restart invalidates the session-level lease. Never publish
        # through another connection after losing ownership of this worker.
        lease.execute(text("SELECT 1"))
        lease.commit()
        with Session(control) as db:
            run = db.scalar(select(RiskModelRun).where(RiskModelRun.id == run_id).with_for_update())
            if run.status != "running" or run.worker_token != token:
                raise RuntimeError("Worker claim was invalidated; candidate not published")
            run.result, run.status, run.finished_at = result, "candidate", datetime.now(UTC)
            from app.models.risk_model import RiskModelEvent

            db.add(
                RiskModelEvent(
                    actor_id=run.created_by_id,
                    run_id=run.id,
                    action="training_completed",
                    details={"source": "synthetic", "data_sha256": result["data_sha256"]},
                )
            )
            db.commit()
    except Exception as failure:
        settings.database_url = source_url
        with Session(control) as db:
            run = db.scalar(select(RiskModelRun).where(RiskModelRun.id == run_id).with_for_update())
            if run.status == "running" and run.worker_token == token:
                run.status = "failed"
                run.error_code = (
                    "insufficient_training_data"
                    if isinstance(failure, ValueError)
                    and any(
                        word in str(failure)
                        for word in ("Insufficient", "Both classes", "no training evidence")
                    )
                    else "training_failed_review_worker"
                )
                run.finished_at = datetime.now(UTC)
                db.commit()
        # Deliberately avoid printing database URLs, names or extracted records.
        raise RuntimeError("Demonstration training failed; dataset retained") from None
    finally:
        isolated.dispose()


if __name__ == "__main__":
    execute(UUID(sys.argv[1]))
