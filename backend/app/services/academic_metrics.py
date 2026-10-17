"""Reference metrics use captured weights and never replace missing evidence by zero.

Risk thresholds already used by reports are retained; missing dimensions cannot
establish a low-risk conclusion. Configurable formulas remain preview-only.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from app.models.academic import AttendanceRecord, GradeRecord


@dataclass(frozen=True)
class AcademicMetrics:
    average_score: float | None
    attendance_rate: float | None
    grade_count: int
    grade_weight_sum: float
    attendance_count: int
    synthetic_count: int = 0
    recorded_average_score: float | None = None

    @property
    def risk_level(self) -> str:
        score = self.recorded_average_score if self.synthetic_count else self.average_score
        rate = self.attendance_rate
        if score is not None and score < 10:
            return "ALTO"
        if (score is not None and score < 12) or (rate is not None and rate < 70):
            return "MEDIO"
        if score is None and rate is None:
            return "SIN_DATOS"
        if score is None or rate is None:
            return "INCOMPLETO"
        return "BAJO"


def academic_metrics(
    grades: Iterable[GradeRecord], attendance: Iterable[AttendanceRecord]
) -> AcademicMetrics:
    grades = [g for g in grades if not getattr(g, "superseded_by_id", None)]
    attendance = list(attendance)
    recorded = [g for g in grades if getattr(g, "data_origin", "recorded") != "synthetic"]
    recorded_weight = sum(g.assessment_weight for g in recorded)
    weight = sum(record.assessment_weight for record in grades)
    return AcademicMetrics(
        average_score=sum(record.score * record.assessment_weight for record in grades) / weight
        if weight > 0
        else None,
        attendance_rate=100
        * sum(record.status == "PRESENT" for record in attendance)
        / len(attendance)
        if attendance
        else None,
        grade_count=len(grades),
        grade_weight_sum=weight,
        attendance_count=len(attendance),
        synthetic_count=len(grades) - len(recorded),
        recorded_average_score=sum(g.score * g.assessment_weight for g in recorded)
        / recorded_weight
        if recorded_weight
        else None,
    )
