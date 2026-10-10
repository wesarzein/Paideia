import pandas as pd
import pytest

from app.endpoints.imports import _canonicalize_frame, _roster_name_parts


@pytest.mark.parametrize(
    "name,expected",
    [
        ("  APELLIDO SINTETICO ALUMNO UNO  ", ("APELLIDO SINTETICO", "ALUMNO UNO")),
        ("DE LA CRUZ, ALUMNO UNO", ("DE LA CRUZ", "ALUMNO UNO")),
        ("SINTETICO ALUMNO", ("", "")),
        ("", ("", "")),
    ],
)
def test_reviewable_name_boundary(name, expected):
    assert _roster_name_parts(name) == expected


def test_mixed_full_names_keep_both_given_names_and_surnames():
    result = _canonicalize_frame(
        pd.DataFrame(
            {
                "Código": ["X", "Y"],
                "Nombre y apellidos": ["APELLIDO SINTETICO ALUMNO UNO", "DE LA CRUZ, ALUMNO DOS"],
            }
        )
    )
    assert list(result["first_name"]) == ["ALUMNO UNO", "ALUMNO DOS"]
    assert list(result["last_name"]) == ["APELLIDO SINTETICO", "DE LA CRUZ"]
