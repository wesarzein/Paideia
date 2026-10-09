from uuid import UUID

from pydantic import BaseModel


class StudentReport(BaseModel):
    student_id: UUID
    student_code: str = ""
    student_name: str
    average_score: float | None
    attendance_rate: float | None
    grade_count: int
    grade_weight_sum: float
    attendance_count: int
    risk_level: str


class ReportSummary(BaseModel):
    total_students: int
    average_score: float | None
    attendance_rate: float | None
    at_risk_count: int
