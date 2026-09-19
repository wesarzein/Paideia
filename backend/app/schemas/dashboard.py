from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_students: int
    active_students: int
    average_score: float
    attendance_rate: float
    at_risk_count: int


class RiskAlert(BaseModel):
    student_id: str
    student_name: str
    average_score: float
    attendance_rate: float
    risk_level: str
