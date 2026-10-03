import re
import unicodedata

from pydantic import BaseModel, field_validator

EVIDENCE_TYPES = (
    "Actitud ante el área",
    "Cuaderno",
    "Módulo",
    "Exposición-Trabajos",
    "Evaluación",
)


def _key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", normalized)


_ALIASES = {
    "actitudanteelarea": "Actitud ante el área",
    "actitud": "Actitud ante el área",
    "cuaderno": "Cuaderno",
    "modulo": "Módulo",
    "exposiciontrabajos": "Exposición-Trabajos",
    "exposicion": "Exposición-Trabajos",
    "trabajos": "Exposición-Trabajos",
    "trabajo": "Exposición-Trabajos",
    "evaluacion": "Evaluación",
    "examen": "Evaluación",
    "tarea": "Exposición-Trabajos",
    "practica": "Módulo",
}


def normalize_evidence_type(value: str) -> str:
    normalized = _ALIASES.get(_key(value.strip()))
    if normalized is None:
        allowed = ", ".join(EVIDENCE_TYPES)
        raise ValueError(f"Tipo de evidencia inválido. Valores permitidos: {allowed}")
    return normalized


class EvidenceTypeModel(BaseModel):
    @field_validator("evaluation_type", mode="before", check_fields=False)
    @classmethod
    def validate_evidence_type(cls, value: str | None) -> str | None:
        return normalize_evidence_type(value) if value is not None else None
