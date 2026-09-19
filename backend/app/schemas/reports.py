from uuid import UUID

from pydantic import BaseModel


class StudentReport(BaseModel):
    student_id: UUID
    student_name: str
    average_score: float
    attendance_rate: float
    risk_level: str


class ReportSummary(BaseModel):
    total_students: int
    average_score: float
    attendance_rate: float
    at_risk_count: int
