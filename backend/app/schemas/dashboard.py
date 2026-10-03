from pydantic import BaseModel, Field


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
    risk_factors: list[str] = Field(default_factory=list)
    recommendation: str
    detection_method: str = "rules_fallback"
