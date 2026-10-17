from io import BytesIO
from uuid import UUID, uuid4

from openpyxl import load_workbook
from sqlalchemy import select
from test_academic_authorization import scenario, sessions

from app.models.academic import GradeRecord

__all__ = ["scenario", "sessions"]


def test_monthly_simulation_is_visible_without_duplicate_evidence_or_real_risk(scenario, sessions):
    client, ids, _, _ = scenario
    with sessions() as db:
        old = db.scalars(
            select(GradeRecord).where(
                GradeRecord.student_id == UUID(ids["students"][0]),
                GradeRecord.course_id == UUID(ids["courses"][0]),
            )
        ).one()
        replacement = GradeRecord(
            id=uuid4(),
            student_id=old.student_id,
            course_id=old.course_id,
            period_id=old.period_id,
            record_kind="historical_bimester",
            assessment_date=None,
            academic_month=4,
            academic_bimester=1,
            evaluation_block=1,
            data_origin="synthetic",
            score=0,
            evaluation_name="Synthetic monthly history",
        )
        db.add(replacement)
        db.flush()
        old.superseded_by_id = replacement.id
        old_id, replacement_id = str(old.id), str(replacement.id)
        db.commit()
    listed = client.get("/grades", params={"student_id": ids["students"][0], "month": 4}).json()
    assert [r["id"] for r in listed] == [replacement_id]
    assert listed[0]["data_origin"] == "synthetic" and listed[0]["assessment_date"] is None
    catalog = client.get("/academic/catalog")
    assert catalog.status_code == 200
    assert catalog.json()["periods"][0]["bimester_months"] == {"4": 1}
    reports = client.get(
        "/reports/students", params={"month": 4, "course_id": ids["courses"][0]}
    ).json()
    pupil = next(r for r in reports if r["student_id"] == ids["students"][0])
    assert pupil["average_score"] == 0 and pupil["synthetic_count"] == 1
    assert pupil["risk_level"] not in {"ALTO", "MEDIO"}
    exported = client.get("/reports/export.xlsx", params={"grade_id": ids["grade"], "month": 4})
    assert exported.status_code == 200
    sheet = load_workbook(BytesIO(exported.content), read_only=True).active
    columns = next(sheet.values)
    assert "average_score" in columns
    assert "synthetic_count" not in columns and "recorded_count" not in columns
    assert client.patch(f"/grades/{old_id}", json={"score": 15}).status_code == 409
    assert client.delete(f"/grades/{old_id}").status_code == 409
    assert client.delete(f"/grades/{replacement_id}").status_code == 409
