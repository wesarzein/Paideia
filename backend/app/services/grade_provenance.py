"""Monthly identity does not invent an individual assessment date."""

from sqlalchemy import extract, func

from app.models.academic import GradeRecord


def month_expression():
    return func.coalesce(GradeRecord.academic_month, extract("month", GradeRecord.assessment_date))


def origin_counts(rows):
    return {
        origin: sum(getattr(r, "data_origin", "recorded") == origin for r in rows)
        for origin in ("recorded", "excel", "synthetic")
    }
