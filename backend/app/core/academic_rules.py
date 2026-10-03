LITERAL_GRADE_THRESHOLDS = (
    (16.4, "AD"),
    (13.4, "A"),
    (10.4, "B"),
)

RISK_THRESHOLDS = {"average": 12.0, "high_average": 10.0, "attendance_percent": 70.0, "high_attendance_percent": 60.0}


def literal_grade(score: float) -> str:
    for threshold, label in LITERAL_GRADE_THRESHOLDS:
        if score > threshold:
            return label
    return "C"