import os
import subprocess
import sys
from threading import Thread
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.config import settings
from app.core.database import get_db
from app.models.risk_model import RiskModelEvent, RiskModelRun
from app.models.user import User
from app.services import risk_registry
from app.services.local_risk_model import predict_demonstration

router = APIRouter()
Admin = Annotated[User, Depends(require_roles("admin"))]
Staff = Annotated[User, Depends(require_roles("admin", "teacher", "coordinator", "director"))]
Database = Annotated[Session, Depends(get_db)]


class DemoTraining(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = Field(default=42, ge=0, le=2147483647)
    pupils: int = Field(default=80, ge=80, le=200)
    failure_cutoff: float = Field(default=10.4, ge=0, le=20)
    medium_probability: float = Field(default=0.3, ge=0, le=1)
    high_probability: float = Field(default=0.7, gt=0, le=1)
    acknowledge_synthetic: bool

    @model_validator(mode="after")
    def ordered_thresholds(self):
        if self.medium_probability >= self.high_probability:
            raise ValueError("El umbral medio debe ser menor que el alto")
        return self


class ModelDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=500)]
    acknowledge_synthetic: bool


class ModelActivation(ModelDecision):
    run_id: UUID | None = None
    expected_version: int = Field(ge=0)


def summary(run):
    result = run.result or {}
    return {
        "id": str(run.id),
        "mode": run.mode,
        "status": run.status,
        "configuration": run.configuration,
        "created_at": run.created_at,
        "finished_at": run.finished_at,
        "approved_at": run.approved_at,
        "started_at": run.started_at,
        "created_by_id": str(run.created_by_id),
        "approved_by_id": str(run.approved_by_id) if run.approved_by_id else None,
        "error_code": run.error_code,
        "metrics": result.get("metrics"),
        "baseline": result.get("baseline"),
        "split": result.get("split"),
        "lineage": result.get("lineage"),
        "limitation": result.get("limitation"),
        "parameters": result.get("parameters"),
        "data_sha256": result.get("data_sha256"),
    }


@router.get("")
def models(db: Database, _user: Staff):
    active = risk_registry.deployment(db)
    return {
        "mode": "demonstration",
        "institutional_status": "inactive_policy_and_data_required",
        "active_run_id": str(active.run_id) if active.run_id else None,
        "deployment_version": active.version,
        "autorun": os.environ.get("PAIDEIA_AI_AUTORUN") == "true",
        "worker_active": risk_registry.worker_active(db),
        "runs": [
            summary(r)
            for r in db.scalars(
                select(RiskModelRun)
                .where(RiskModelRun.mode == "demonstration")
                .order_by(RiskModelRun.created_at.desc())
            )
        ],
    }


def launch_worker(run_id):
    process = subprocess.Popen(
        [sys.executable, "-m", "app.ai_worker", str(run_id)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    # Reap the one-off child outside the HTTP response lifecycle.
    Thread(target=process.wait, daemon=True).start()


@router.post("/{run_id}/recover")
def recover(run_id: UUID, payload: ModelDecision, db: Database, user: Admin):
    if not payload.acknowledge_synthetic:
        raise HTTPException(422, "Confirma la recuperación exclusivamente demostrativa")
    return summary(risk_registry.recover_interrupted(db, user, run_id, payload.reason))


@router.post("/demonstration/train", status_code=202)
def train(payload: DemoTraining, tasks: BackgroundTasks, db: Database, user: Admin):
    if not payload.acknowledge_synthetic:
        raise HTTPException(422, "Confirma que son datos ficticios, sin eficacia institucional")
    run = risk_registry.queue_training(
        db, user, payload.model_dump(exclude={"acknowledge_synthetic"})
    )
    if os.environ.get("PAIDEIA_AI_AUTORUN") == "true":
        tasks.add_task(launch_worker, run.id)
    return summary(run)


@router.post("/{run_id}/approve")
def approve(run_id: UUID, payload: ModelDecision, db: Database, user: Admin):
    if not payload.acknowledge_synthetic:
        raise HTTPException(422, "Aprobación exclusivamente experimental requerida")
    return summary(risk_registry.approve(db, user, run_id, payload.reason))


@router.post("/demonstration/activate")
def activate(payload: ModelActivation, db: Database, user: Admin):
    if not payload.acknowledge_synthetic:
        raise HTTPException(422, "Activación exclusivamente demostrativa requerida")
    active = risk_registry.activate(
        db, user, payload.run_id, payload.expected_version, payload.reason
    )
    return {
        "active_run_id": str(active.run_id) if active.run_id else None,
        "deployment_version": active.version,
    }


@router.get("/events")
def events(db: Database, _user: Admin):
    return [
        {
            "id": str(e.id),
            "run_id": str(e.run_id) if e.run_id else None,
            "actor_id": str(e.actor_id),
            "action": e.action,
            "details": e.details,
            "created_at": e.created_at,
        }
        for e in db.scalars(
            select(RiskModelEvent).order_by(RiskModelEvent.created_at.desc()).limit(100)
        )
    ]


@router.get("/demonstration/predictions")
def predictions(db: Database, _user: Staff):
    active = risk_registry.deployment(db)
    if not active.run_id:
        return {"status": "untrained_or_inactive", "mode": "demonstration", "rows": []}
    run = db.get(RiskModelRun, active.run_id)
    engine = None
    try:
        if run is None or run.status != "approved" or run.mode != "demonstration":
            raise ValueError("No approved demonstration model")
        engine = risk_registry.demo_engine(settings.database_url, run.dataset_schema)
        rows = risk_registry.dataset_rows(engine, run.dataset_schema)
        inferred = [
            {**r, "prediction": predict_demonstration(run.result["artifact"], r)} for r in rows
        ]
    except (ValueError, KeyError, IndexError, TypeError, AssertionError, SQLAlchemyError) as exc:
        raise HTTPException(503, "Conjunto demostrativo no disponible") from exc
    finally:
        if engine is not None:
            engine.dispose()
    return {
        "status": "experimental_not_institutionally_validated",
        "mode": "demonstration",
        "run_id": str(run.id),
        "model_date": run.finished_at,
        "rows": inferred,
    }
