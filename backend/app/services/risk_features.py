"""Minimized course-level features from periods strictly before a target period.

This extractor does not infer missing evaluations or a student's future outcome.
Names, codes, notes and contact information never enter the feature matrix.
"""

from collections import defaultdict

from app.services.academic_metrics import academic_metrics

FEATURE_NAMES = (
    "previous_average",
    "score_trend",
    "present_fraction",
    "late_fraction",
    "grade_count",
    "history_coverage",
    "literal_c_fraction",
)


def historical_features(grades, attendance, periods, target_period_id, minimum_periods=2):
    target = next(p for p in periods if p.id == target_period_id)
    previous = sorted(
        (p for p in periods if p.ends_on < target.starts_on), key=lambda p: (p.ends_on, str(p.id))
    )
    previous_ids = {p.id for p in previous}
    grouped, attendance_groups = defaultdict(list), defaultdict(list)
    for row in grades:
        if row.period_id in previous_ids and (row.assessment_date is None or row.assessment_date < target.starts_on):
            grouped[(row.student_id, row.course_id)].append(row)
    for row in attendance:
        if row.period_id in previous_ids and row.attendance_date < target.starts_on:
            attendance_groups[(row.student_id, row.course_id)].append(row)
    results = []
    for (student_id, course_id), rows in sorted(grouped.items(), key=lambda i: str(i[0])):
        means = [
            academic_metrics([r for r in rows if r.period_id == p.id], []).average_score
            for p in previous
        ]
        available = [m for m in means if m is not None]
        records = attendance_groups[(student_id, course_id)]
        metrics = academic_metrics(rows, records)
        results.append(
            {
                "student_id": str(student_id),
                "course_id": str(course_id),
                "target_period_id": str(target.id),
                "status": "ready" if len(available) >= minimum_periods else "insufficient_history",
                "history_periods": len(available),
                "attendance_count": len(records),
                "features": [
                    available[-1] if available else None,
                    available[-1] - available[-2] if len(available) >= 2 else None,
                    metrics.attendance_rate / 100 if records else None,
                    sum(r.status == "LATE" for r in records) / len(records) if records else None,
                    len(rows),
                    len(available) / len(previous) if previous else 0,
                    sum(r.score <= 10.4 for r in rows) / len(rows),
                ],
            }
        )
    return results
