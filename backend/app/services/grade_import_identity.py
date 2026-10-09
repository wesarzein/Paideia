"""Compare imports with saved grades; never overwrite without reviewed consent."""

import hashlib
import hmac
import json

from fastapi import HTTPException
from sqlalchemy import func, select, text

from app.core.config import settings
from app.models.academic import CourseAssessmentComponent, GradeRecord
from app.models.user import AuditLog


def identity(record, *, component=True):
    return json.dumps(
        [
            str(record.student_id),
            str(record.course_id),
            str(record.period_id),
            str(record.component_id) if component and record.component_id else None,
            record.evaluation_name.strip(),
            record.evaluation_type.strip(),
            record.assessment_date.isoformat(),
        ],
        ensure_ascii=False,
    )


def _token(user, incoming, existing):
    content = json.dumps(
        {
            "actor": str(user.id),
            "identity": identity(incoming),
            "incoming": [incoming.score, incoming.qualitative_note],
            "existing": [
                str(existing.id),
                existing.score,
                existing.qualitative_note,
            existing.updated_at.isoformat() if existing.updated_at else None,
                existing.assessment_config,
            ],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hmac.new(settings.jwt_secret_key.encode(), content.encode(), hashlib.sha256).hexdigest()


def inspect_rows(db, user, incoming, raw_rows, *, lock=False):
    if lock and db.bind.dialect.name == "postgresql":
        # Sorted acquisition prevents opposite-order batches from deadlocking.
        for key in sorted({identity(record, component=False) for record in incoming}):
            db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key}
            )
    reviews, existing_records, errors, seen = [], [], [], {}
    for index, (record, raw) in enumerate(zip(incoming, raw_rows, strict=True), 1):
        query = select(GradeRecord).where(
            GradeRecord.student_id == record.student_id,
            GradeRecord.course_id == record.course_id,
            GradeRecord.period_id == record.period_id,
            func.trim(GradeRecord.evaluation_name) == record.evaluation_name,
            func.trim(GradeRecord.evaluation_type) == record.evaluation_type,
            GradeRecord.assessment_date == record.assessment_date,
        )
        # Missing criterion is resolved only when the match is unambiguous.
        explicit_component = "component_id" in raw and raw["component_id"] != ""
        if explicit_component:
            query = query.where(GradeRecord.component_id == record.component_id)
        if lock:
            query = query.with_for_update()
        matches = list(db.scalars(query))
        existing = matches[0] if len(matches) == 1 else None
        item = {
            "row": index,
            "status": "new",
            "component_id": None,
            "existing": None,
            "review_token": None,
        }
        if len(matches) > 1:
            item["status"] = "ambiguous"
            errors.append(
                {
                    "row": index,
                    "error": "Identidad ambigua: indica el criterio o revisa el grupo histórico",
                }
            )
        elif existing:
            record.component_id = existing.component_id
            item["existing"] = {
                "id": str(existing.id),
                "score": existing.score,
                "qualitative_note": existing.qualitative_note,
            }
            item["status"] = (
                "identical"
                if (
                    record.score == existing.score
                    and record.qualitative_note == existing.qualitative_note
                )
                else "different"
            )
            item["review_token"] = _token(user, record, existing)
        else:
            if not explicit_component:
                component = db.scalar(
                    select(CourseAssessmentComponent).where(
                        CourseAssessmentComponent.course_id == record.course_id,
                        CourseAssessmentComponent.name == record.evaluation_type,
                    )
                )
                if component:
                    record.component_id = component.id
            if record.component_id:
                component = db.get(CourseAssessmentComponent, record.component_id)
                if not component or not component.is_active:
                    errors.append(
                        {"row": index, "error": "El criterio de la nota nueva no está activo"}
                    )
        item["component_id"] = str(record.component_id) if record.component_id else None
        key = identity(record)
        values = (record.score, record.qualitative_note)
        if key in seen:
            if seen[key] != values:
                errors.append(
                    {
                        "row": index,
                        "error": "La misma identidad tiene valores distintos dentro del archivo",
                    }
                )
            elif item["status"] != "ambiguous":
                item["status"] = "duplicate_in_file"
        seen[key] = values
        reviews.append(item)
        existing_records.append(existing)
    return reviews, existing_records, errors


def commit_rows(db, user, incoming, raw_rows):
    reviews, existing, errors = inspect_rows(db, user, incoming, raw_rows, lock=True)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})
    operations = []
    for record, raw, item, saved in zip(incoming, raw_rows, reviews, existing, strict=True):
        decision = raw.get("decision")
        if decision not in (None, "", "keep", "update"):
            raise HTTPException(status_code=422, detail="Decisión de importación inválida")
        if item["status"] == "different":
            if decision not in ("keep", "update"):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Revisa las diferencias y decide conservar o actualizar",
                        "rows": reviews,
                    },
                )
            if decision == "update" and not hmac.compare_digest(
                str(raw.get("review_token") or ""), item["review_token"]
            ):
                raise HTTPException(
                    status_code=409,
                    detail="La nota o la propuesta cambió; revisa nuevamente antes de actualizar",
                )
        if item["status"] == "new" and raw.get("review_token"):
            raise HTTPException(
                status_code=409, detail="El registro revisado ya no coincide; revisa nuevamente"
            )
        operations.append((record, saved, item["status"], decision))
    counts = {"processed": len(incoming), "imported": 0, "updated": 0, "skipped": 0, "rejected": 0}
    for record, saved, state, decision in operations:
        if state == "new":
            db.add(record)
            counts["imported"] += 1
        elif state == "different" and decision == "update":
            db.add(
                AuditLog(
                    actor_email=getattr(user, "email", str(user.id)),
                    action="grade_import_update",
                    entity="grade_records",
                    details=json.dumps(
                        {
                            "id": str(saved.id),
                            "previous_score": saved.score,
                            "score": record.score,
                            "qualitative_note_changed": saved.qualitative_note
                            != record.qualitative_note,
                        }
                    ),
                )
            )
            saved.score = record.score
            saved.qualitative_note = record.qualitative_note
            counts["updated"] += 1
        else:
            counts["skipped"] += 1
    db.commit()
    return counts
