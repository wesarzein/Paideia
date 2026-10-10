"""Separate synthetic-model summary; never merge these counts with academic KPIs."""

from collections import Counter

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.models.risk_model import RiskModelDeployment, RiskModelRun
from app.services.local_risk_model import predict_demonstration
from app.services.risk_registry import dataset_rows, demo_engine


def demonstration_summary(db):
    active = db.scalar(
        select(RiskModelDeployment).where(RiskModelDeployment.mode == "demonstration")
    )
    if active is None or active.run_id is None:
        return {"status": "inactive", "institutional_predictions": False}
    run = db.get(RiskModelRun, active.run_id)
    if run is None or run.status != "approved" or run.mode != "demonstration":
        return {"status": "unavailable", "institutional_predictions": False}
    engine = demo_engine(settings.database_url, run.dataset_schema)
    try:
        rows = dataset_rows(engine, run.dataset_schema)
        predictions = [predict_demonstration(run.result["artifact"], row) for row in rows]
    except (ValueError, KeyError, TypeError, AssertionError, SQLAlchemyError):
        return {"status": "unavailable", "institutional_predictions": False}
    finally:
        engine.dispose()
    counts = Counter(p["risk"] for p in predictions)
    return {
        "status": "demonstration_only",
        "institutional_predictions": False,
        "run_id": str(run.id),
        "model_date": run.finished_at,
        "cases": len(rows),
        "ready": len(rows) - counts[None],
        "insufficient": counts[None],
        "high": counts["high"],
        "medium": counts["medium"],
        "low": counts["low"],
    }
