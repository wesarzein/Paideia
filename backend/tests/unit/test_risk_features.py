from copy import deepcopy
from datetime import date
from types import SimpleNamespace as Row

from app.services.risk_features import FEATURE_NAMES, historical_features


def fixtures():
    periods = [
        Row(id=i, starts_on=date(2020 + i, 1, 1), ends_on=date(2020 + i, 12, 31)) for i in range(3)
    ]
    grades = [
        Row(
            student_id="fictional",
            course_id="course",
            period_id=i,
            score=score,
            assessment_weight=1,
            assessment_date=date(2020 + i, 2, 1),
        )
        for i, score in enumerate([0, 12, 20])
    ]
    return grades, periods


def test_future_grades_and_attendance_cannot_leak_into_predictors():
    grades, periods = fixtures()
    before = historical_features(grades, [], periods, 2)
    altered = deepcopy(grades)
    altered[-1].score = 0
    future_attendance = [
        Row(
            student_id="fictional",
            course_id="course",
            period_id=2,
            attendance_date=date(2022, 2, 1),
            status="ABSENT",
        )
    ]
    assert historical_features(altered, future_attendance, periods, 2) == before
    assert before[0]["features"][:2] == [12, 12]
    assert before[0]["features"][2:4] == [None, None]
    assert before[0]["status"] == "ready"


def test_insufficient_history_and_real_zero_are_distinct():
    grades, periods = fixtures()
    result = historical_features(grades, [], periods, 1)[0]
    assert result["status"] == "insufficient_history"
    assert result["features"][0] == 0
    assert result["features"][1] is None
    assert not any(s in " ".join(FEATURE_NAMES) for s in ("name", "email", "document"))
