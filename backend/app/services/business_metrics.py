"""Read-only indicators over scoped evidence; never official formula results."""

from collections import Counter, defaultdict
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.academic_rules import literal_grade
from app.models.academic import (
    AcademicPeriod,
    AttendanceRecord,
    Course,
    Enrollment,
    EvaluationConfigurationRevision,
    Grade,
    GradeRecord,
)
from app.models.student import Student
from app.services.academic_access import record_scope, student_scope
from app.services.academic_metrics import academic_metrics


def indicators(db, user, filters):
    query = select(Student).where(student_scope(user, filters.get("course_id")))
    for field in ("grade_id", "section_id", "student_id"):
        if filters.get(field):
            column = Student.id if field == "student_id" else getattr(Student, field)
            query = query.where(column == filters[field])
    if filters.get("level"):
        query = query.join(Grade).where(Grade.level == filters["level"])
    students = db.scalars(query).all()

    def evidence(model):
        query = select(model).where(
            model.student_id.in_([p.id for p in students]), record_scope(model, user)
        )
        for field in ("period_id", "course_id"):
            if filters.get(field):
                query = query.where(getattr(model, field) == filters[field])
        if model is GradeRecord and filters.get("bimester"):
            query = query.where(model.academic_bimester == filters["bimester"])
        return db.scalars(query).all()

    grades, attendance, enrollments = (
        evidence(GradeRecord),
        evidence(AttendanceRecord),
        evidence(Enrollment),
    )
    expected = {
        (e.student_id, e.course_id, e.period_id) for e in enrollments if e.status == "ACTIVE"
    }
    observed = {(g.student_id, g.course_id, g.period_id) for g in grades}
    counts = Counter(a.status for a in attendance)
    metrics = academic_metrics(grades, attendance)
    distribution = Counter(literal_grade(g.score) for g in grades)
    groups = {field: defaultdict(list) for field in ("period", "month", "course", "student")}
    for g in grades:
        for field, key in (
            ("period", g.period_id),
            ("month", g.assessment_date.strftime("%Y-%m")),
            ("course", g.course_id),
            ("student", g.student_id),
        ):
            groups[field][key].append(g)
    courses = {
        c.id: c.name for c in db.scalars(select(Course).where(Course.id.in_(groups["course"])))
    }
    periods = {p.id: p for p in db.scalars(select(AcademicPeriod))}
    revisions = {
        r.id: r.configuration
        for r in db.scalars(
            select(EvaluationConfigurationRevision).where(
                EvaluationConfigurationRevision.id.in_(
                    {g.evaluation_revision_id for g in grades if g.evaluation_revision_id}
                )
            )
        )
    }
    evaluation_groups = defaultdict(set)
    for g in grades:
        if g.evaluation_revision_id:
            evaluation_groups[
                (
                    g.student_id,
                    g.course_id,
                    g.period_id,
                    g.academic_bimester,
                    g.evaluation_block,
                    g.evaluation_revision_id,
                )
            ].add(g.evaluation_criterion_key)
    completion = Counter()
    for context, recorded in evaluation_groups.items():
        criteria = [
            c
            for c in revisions[context[-1]]["criteria"]
            if c["is_active"] and c["block"] == context[-2]
        ]
        required = {c["key"] for c in criteria if not c["is_optional"]}
        optional = {c["key"] for c in criteria if c["is_optional"]}
        completion["required_complete" if required <= recorded else "required_incomplete"] += 1
        completion["optional_missing"] += bool(optional - recorded)
    attendance_months = defaultdict(Counter)
    for a in attendance:
        attendance_months[a.attendance_date.strftime("%Y-%m")][a.status] += 1

    def aggregate(key, rows, name=None):
        m = academic_metrics(rows, [])
        return {
            "id": str(key),
            "name": name or str(key),
            "count": m.grade_count,
            "average": m.average_score,
            "weight_sum": m.grade_weight_sum,
        }

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "calculation": "reference_captured_weights_not_official_formula",
        "literal_rule": "template_strict_gt_16.4_13.4_10.4",
        "scope": "single_course"
        if len(courses) == 1
        else "multiple_courses"
        if courses
        else "no_course_evidence",
        "students_in_scope": len(students),
        "students_with_grades": len(groups["student"]),
        "grade_count": metrics.grade_count,
        "average": metrics.average_score,
        "zero_scores": sum(g.score == 0 for g in grades),
        "weight_sum": metrics.grade_weight_sum,
        "literal_distribution": {label: distribution[label] for label in ("AD", "A", "B", "C")},
        "numeric_distribution": {
            label: sum((low < g.score <= high) or (low == 0 and g.score == 0) for g in grades)
            for label, low, high in (
                ("0–5", 0, 5),
                (">5–10", 5, 10),
                (">10–15", 10, 15),
                (">15–20", 15, 20),
            )
        },
        "evaluation_coverage": {
            "required_complete": completion["required_complete"],
            "required_incomplete": completion["required_incomplete"],
            "optional_missing": completion["optional_missing"],
            "legacy_records_unknown": sum(not g.evaluation_revision_id for g in grades),
            "basis": "recorded_contexts_historical_revision_not_official_results",
        },
        "coverage": {
            "active_enrollments": len(expected),
            "with_grades": len(expected & observed),
            "without_grades": len(expected - observed),
            "percent": 100 * len(expected & observed) / len(expected) if expected else None,
            "recorded_without_active_enrollment": len(observed - expected),
            "evaluation_completion": "unknown_without_expected_schedule",
        },
        "attendance": {
            "count": len(attendance),
            "present": counts["PRESENT"],
            "absent": counts["ABSENT"],
            "late": counts["LATE"],
            "present_percent": metrics.attendance_rate,
            "absent_percent": 100 * counts["ABSENT"] / len(attendance) if attendance else None,
            "late_percent": 100 * counts["LATE"] / len(attendance) if attendance else None,
            "scope": "full_period_not_bimester",
            "students_with_repeated_absences": sum(
                n > 1
                for n in Counter(a.student_id for a in attendance if a.status == "ABSENT").values()
            ),
        },
        "periods": [
            aggregate(k, groups["period"][k], periods[k].name)
            for k in sorted(groups["period"], key=lambda k: (periods[k].starts_on, str(k)))
        ],
        "attendance_months": [
            {
                "month": k,
                "present": v["PRESENT"],
                "absent": v["ABSENT"],
                "late": v["LATE"],
                "count": sum(v.values()),
            }
            for k, v in sorted(attendance_months.items())
        ],
        "months": [aggregate(k, rows) for k, rows in sorted(groups["month"].items())],
        "courses": [
            aggregate(k, rows, courses[k])
            for k, rows in sorted(groups["course"].items(), key=lambda item: str(item[0]))
        ],
        "students": [
            aggregate(p.id, groups["student"].get(p.id, []), p.student_code or str(p.id))
            for p in students
        ],
        "ai": {"status": "not_enabled", "institutional_predictions": False},
    }
