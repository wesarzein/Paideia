"""Explicit demo approval/deployment; synthetic models cannot enter institutional mode."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, text

from app.models.risk_model import RiskModelDeployment, RiskModelEvent, RiskModelRun
from app.services.local_risk_model import validate_artifact


def event(db, actor, action, run=None, **details):
    db.add(
        RiskModelEvent(
            actor_id=actor.id, action=action, run_id=run.id if run else None, details=details
        )
    )


def acquire_worker_lock(connection):
    if connection.dialect.name != "postgresql":
        raise ValueError("Worker recovery requires PostgreSQL")
    key = connection.scalar(
        text(
            "SELECT hashtextextended(current_database() || ':' || current_schema() || :suffix, 0)"
        ),
        {"suffix": ":paideia-demo-worker"},
    )
    return (
        key if connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}) else None
    )


def release_worker_lock(connection, key):
    connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})


def worker_active(db):
    connection = db.connection()
    if connection.dialect.name != "postgresql":
        return None
    key = acquire_worker_lock(connection)
    if key is None:
        return True
    release_worker_lock(connection, key)
    return False


def recover_interrupted(db, actor, run_id, reason):
    connection = db.connection()
    try:
        key = acquire_worker_lock(connection)
    except ValueError as exc:
        raise HTTPException(503, "Recuperación disponible únicamente con PostgreSQL") from exc
    if key is None:
        raise HTTPException(409, "Un proceso de entrenamiento sigue activo; no se puede recuperar")
    try:
        deployment(db, lock=True)
        run = db.scalar(select(RiskModelRun).where(RiskModelRun.id == run_id).with_for_update())
        if run is None:
            raise HTTPException(404, "Entrenamiento no encontrado")
        if run.mode != "demonstration" or run.status not in {"queued", "running"}:
            raise HTTPException(409, "Solo se recuperan solicitudes demostrativas interrumpidas")
        run.status = "failed"
        run.error_code = "interrupted_recovered_request_new_training"
        run.worker_token = None
        run.finished_at = datetime.now(UTC)
        event(db, actor, "training_recovered", run, reason=reason, dataset_preserved=True)
        db.flush()
    finally:
        release_worker_lock(connection, key)
    db.commit()
    return run


def deployment(db, lock=False):
    query = select(RiskModelDeployment).where(RiskModelDeployment.mode == "demonstration")
    if lock:
        query = query.with_for_update()
    row = db.scalar(query)
    if row is None:
        # SQLite metadata fixtures do not execute Alembic data migrations.
        row = RiskModelDeployment(mode="demonstration", version=0)
        db.add(row)
        db.flush()
    return row


def queue_training(db, actor, configuration):
    deployment(db, lock=True)
    if db.scalar(select(RiskModelRun.id).where(RiskModelRun.status.in_(["queued", "running"]))):
        raise HTTPException(409, "Ya existe un entrenamiento pendiente o en ejecución")
    run = RiskModelRun(
        mode="demonstration",
        status="queued",
        dataset_schema="ai_demo_" + uuid4().hex,
        created_by_id=actor.id,
        configuration=configuration,
    )
    db.add(run)
    db.flush()
    event(db, actor, "training_requested", run, source="synthetic", config=configuration)
    db.commit()
    return run


def approve(db, actor, run_id, reason):
    run = db.scalar(select(RiskModelRun).where(RiskModelRun.id == run_id).with_for_update())
    if run is None:
        raise HTTPException(404, "Modelo no encontrado")
    if run.mode != "demonstration" or run.status != "candidate" or not run.result:
        raise HTTPException(409, "Solo un candidato demostrativo evaluado puede aprobarse")
    try:
        validate_artifact(run.result.get("artifact", {}))
        if (
            run.result["split"]["student_overlap"] != 0
            or run.result["split"]["test_count"] < 20
            or run.result["lineage"]["personal_data"] is not False
        ):
            raise ValueError("Invalid demonstration evaluation")
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(409, "Artefacto o evaluación no válidos") from exc
    run.status = "approved"
    run.approved_by_id = actor.id
    run.approved_at = datetime.now(UTC)
    event(db, actor, "demo_approved", run, reason=reason, institutional_validation=False)
    db.commit()
    return run


def activate(db, actor, run_id, expected_version, reason):
    active = deployment(db, lock=True)
    if active.version != expected_version:
        raise HTTPException(409, "La versión activa cambió; recarga antes de continuar")
    run = db.get(RiskModelRun, run_id) if run_id else None
    if run_id and (run is None or run.mode != "demonstration" or run.status != "approved"):
        raise HTTPException(409, "El modelo debe estar aprobado exclusivamente para demostración")
    previous = str(active.run_id) if active.run_id else None
    active.run_id = run.id if run else None
    active.version += 1
    event(
        db,
        actor,
        "demo_activated" if run else "demo_deactivated",
        run,
        previous_run_id=previous,
        deployment_version=active.version,
        reason=reason,
    )
    db.commit()
    return active


def demo_engine(url, schema):
    import re

    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    if not re.fullmatch(r"ai_demo_[0-9a-f]{32}", schema):
        raise ValueError("Invalid internal demo schema")
    # No public fallback: all academic records come exclusively from this dataset.
    return create_engine(make_url(url).update_query_dict({"options": f"-csearch_path={schema}"}))


def dataset_rows(engine, schema):
    from sqlalchemy.orm import Session

    from app.models.academic import AcademicPeriod, AttendanceRecord, GradeRecord
    from app.services.risk_features import historical_features

    if not schema.startswith("ai_demo_"):
        raise ValueError("Invalid demo source")
    with Session(engine) as db:
        assert db.scalar(text("SELECT current_schema()")) == schema
        periods = db.scalars(select(AcademicPeriod).order_by(AcademicPeriod.starts_on)).all()
        grades = db.scalars(select(GradeRecord)).all()
        attendance = db.scalars(select(AttendanceRecord)).all()
        return historical_features(grades, attendance, periods, periods[-1].id)
