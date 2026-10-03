import pandas as pd

from app.core.academic_rules import literal_grade
from app.endpoints.imports import _canonicalize_frame, _flatten_grade_frame
from app.models.academic import AcademicPeriod


def test_literal_grade_thresholds_are_strict():
    assert literal_grade(16.41) == "AD"
    assert literal_grade(16.4) == "A"
    assert literal_grade(13.4) == "B"
    assert literal_grade(10.4) == "C"


def test_import_headers_accept_accents_aliases_and_combined_student_name():
    frame = pd.DataFrame(
        {
            "Código del alumno": ["TST-001"],
            "Nombre y Apellidos": ["DOE, JANE"],
            "Calificación": [18],
            "Fecha de evaluación": ["2026-04-01"],
        }
    )

    normalized = _canonicalize_frame(frame)

    assert normalized.loc[0, "student_code"] == "TST-001"
    assert normalized.loc[0, "last_name"] == "DOE"
    assert normalized.loc[0, "first_name"] == "JANE"
    assert normalized.loc[0, "score"] == 18
    assert normalized.loc[0, "assessment_date"] == "2026-04-01"


def test_monthly_component_blocks_flatten_dynamically_and_keep_module_optional():
    frame = pd.DataFrame({
        "Código": ["TST-002"],
        "Nombre y Apellidos": ["DOE, JOHN"],
        "4 MES Actitud ante el Área": [17],
        "4 MES Módulo": [18],
        "5 MES Actitud ante el Área": [16],
        "Promedio Mensual": [17],
    })
    period = AcademicPeriod(name="2026", starts_on=pd.Timestamp("2026-03-01").date(), ends_on=pd.Timestamp("2026-12-20").date())

    rows = _flatten_grade_frame(frame, period)

    assert len(rows) == 3
    assert set(rows["evaluation_type"]) == {"Actitud ante el área", "Módulo"}
    assert set(rows["evaluation_name"]) == {"Mes 4", "Mes 5"}
    assert list(rows["assessment_date"]) == ["2026-04-01", "2026-04-01", "2026-05-01"]
