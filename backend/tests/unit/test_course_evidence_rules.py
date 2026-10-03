from datetime import date
from uuid import uuid4

import pandas as pd
import pytest
from pydantic import ValidationError

from app.endpoints.imports import _flatten_grade_frame
from app.models.academic import AcademicPeriod
from app.schemas.grades import GradeCreate
from app.services.course_catalog import canonical_course_name, generate_course_code
from app.services.evidence_types import EVIDENCE_TYPES, normalize_evidence_type


@pytest.mark.parametrize(
    ("abbreviation", "expected"),
    [
        ("Raz. Mat.", "Razonamiento Matemático"),
        ("Com. Lingüística", "Comunicación Lingüística"),
        ("Ed. Física", "Educación Física"),
        ("Trigonomet.", "Trigonometría"),
        ("Ed. por el Trabajo", "Educación para el Trabajo"),
        ("Educación por el Arte", "Educación por el Arte"),
    ],
)
def test_course_names_are_expanded_and_codes_are_stable(
    abbreviation: str, expected: str
) -> None:
    assert canonical_course_name(abbreviation) == expected
    code = generate_course_code(expected)
    assert code == generate_course_code(abbreviation)
    assert code.startswith("CUR-")


@pytest.mark.parametrize(
    ("legacy_value", "expected"),
    [
        ("Actitud ante el área", EVIDENCE_TYPES[0]),
        ("modulo", EVIDENCE_TYPES[2]),
        ("Exposición/Trabajos", EVIDENCE_TYPES[3]),
        ("Tarea", EVIDENCE_TYPES[3]),
        ("Examen", EVIDENCE_TYPES[4]),
    ],
)
def test_evidence_aliases_normalize_to_official_values(
    legacy_value: str, expected: str
) -> None:
    assert normalize_evidence_type(legacy_value) == expected


def test_grade_schema_rejects_non_official_evidence_type() -> None:
    with pytest.raises(ValidationError):
        GradeCreate(
            student_id=uuid4(),
            course_id=uuid4(),
            period_id=uuid4(),
            assessment_date=date(2026, 4, 1),
            score=15,
            evaluation_type="Tarea libre",
        )


def test_monthly_spreadsheet_columns_flatten_with_month_dates() -> None:
    period = AcademicPeriod(
        name="Año escolar 2026",
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 12, 31),
    )
    frame = pd.DataFrame(
        {
            "student_code": ["1SB001"],
            "Actitud ante el área Enero": [18],
            "Cuaderno 1 mes": [17],
        }
    )

    flattened = _flatten_grade_frame(frame, period)

    assert list(flattened["evaluation_type"]) == [
        "Actitud ante el área",
        "Cuaderno",
    ]
    assert list(flattened["assessment_date"]) == [
        "2026-01-01",
        "2026-01-01",
    ]
