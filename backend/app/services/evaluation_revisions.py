"""Persistence adapter for immutable evaluation configuration revisions."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import EvaluationConfigurationRevision
from app.services.evaluation_configuration import Configuration, from_document

REVISION_STATES = frozenset({"draft", "published"})


class StaleEvaluationRevision(ValueError):
    """The client edited a version that is no longer current."""


def latest_revision(
    db: Session, course_id: UUID, period_id: UUID
) -> EvaluationConfigurationRevision | None:
    return db.scalar(
        select(EvaluationConfigurationRevision)
        .where(
            EvaluationConfigurationRevision.course_id == course_id,
            EvaluationConfigurationRevision.period_id == period_id,
        )
        .order_by(EvaluationConfigurationRevision.version.desc())
        .limit(1)
    )


def latest_published_revision(
    db: Session, course_id: UUID, period_id: UUID
) -> EvaluationConfigurationRevision | None:
    return db.scalar(
        select(EvaluationConfigurationRevision)
        .where(
            EvaluationConfigurationRevision.course_id == course_id,
            EvaluationConfigurationRevision.period_id == period_id,
            EvaluationConfigurationRevision.state == "published",
        )
        .order_by(EvaluationConfigurationRevision.version.desc())
        .limit(1)
    )


def create_revision(
    db: Session,
    configuration: Configuration,
    actor_id: UUID,
    reason: str,
    expected_version: int,
    state: str,
) -> EvaluationConfigurationRevision:
    """Stage an append-only revision; the caller owns commit/rollback.

    The unique database constraint is the final guard if concurrent requests both
    observe the same latest version.
    """
    if state not in REVISION_STATES:
        raise ValueError("Estado de revisión inválido")
    if type(expected_version) is not int or expected_version < 0:
        raise ValueError("Versión esperada inválida")
    reason = reason.strip()
    if not reason or len(reason) > 500:
        raise ValueError("Indica un motivo de hasta 500 caracteres")

    course_id = UUID(configuration.course_id)
    period_id = UUID(configuration.period_id)
    previous = latest_revision(db, course_id, period_id)
    current_version = previous.version if previous else 0
    if expected_version != current_version:
        raise StaleEvaluationRevision(
            f"La configuración cambió: esperabas v{expected_version} y la actual es v{current_version}"
        )

    revision = EvaluationConfigurationRevision(
        course_id=course_id,
        period_id=period_id,
        version=current_version + 1,
        state=state,
        previous_revision_id=previous.id if previous else None,
        configuration=configuration.document(),
        content_hash=configuration.fingerprint(),
        reason=reason,
        created_by_id=actor_id,
    )
    db.add(revision)
    db.flush()
    return revision


def revision_configuration(revision: EvaluationConfigurationRevision) -> Configuration:
    configuration = from_document(revision.configuration)
    if configuration.fingerprint() != revision.content_hash:
        raise ValueError("La huella de la configuración guardada no coincide")
    if (
        configuration.course_id != str(revision.course_id)
        or configuration.period_id != str(revision.period_id)
    ):
        raise ValueError("La configuración guardada pertenece a otro ámbito")
    return configuration


def revision_payload(revision: EvaluationConfigurationRevision) -> dict:
    revision_configuration(revision)
    return {
        "id": str(revision.id),
        "course_id": str(revision.course_id),
        "period_id": str(revision.period_id),
        "version": revision.version,
        "state": revision.state,
        "previous_revision_id": (
            str(revision.previous_revision_id) if revision.previous_revision_id else None
        ),
        "configuration": revision.configuration,
        "content_hash": revision.content_hash,
        "reason": revision.reason,
        "created_by_id": str(revision.created_by_id),
        "created_at": revision.created_at.isoformat() if revision.created_at else None,
    }
