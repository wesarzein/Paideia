"""Immutable evaluation documents and draft previews, independent of DB and HTTP.

These are building blocks, not a replacement of the existing grade calculation.
Publication, institutional permissions and grade-version binding require adapters.
"""

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.academic_rules import literal_grade
from app.services.safe_formula import FormulaError, evaluate, number, parse


def identifier(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value):
        raise ValueError("Identificador estable inválido (letras, números y guion bajo)")


def label(value: str, limit=100) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Nombre vacío o demasiado largo")


def position(value) -> None:
    if type(value) is not int or not 0 <= value <= 255:
        raise ValueError("Orden inválido")


def header_key(value: str) -> str:
    text = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', text)


DERIVED_HEADERS = frozenset({'promediomensual', 'promedioliteral', 'ps', 'pf'})


@dataclass(frozen=True)
class Competency:
    key: str
    name: str
    position: int
    is_active: bool = True

    def __post_init__(self):
        identifier(self.key)
        label(self.name)
        position(self.position)
        if type(self.is_active) is not bool:
            raise ValueError("Estado inválido")


@dataclass(frozen=True)
class Criterion:
    key: str
    name: str
    block: int
    position: int
    weight: Decimal = Decimal(1)
    competency_key: str | None = None
    is_active: bool = True
    is_optional: bool = False
    source_header: str | None = None
    legacy_component_id: str | None = None

    def __post_init__(self):
        identifier(self.key)
        label(self.name)
        position(self.position)
        if type(self.block) is not int or self.block not in (1, 2):
            raise ValueError("El bimestre tiene dos bloques")
        if type(self.is_active) is not bool or type(self.is_optional) is not bool:
            raise ValueError("Estado u opcionalidad inválidos")
        weight = number(self.weight)
        # Reuse the existing component range; weights are relative, not percentages.
        if not 0 <= weight <= 100:
            raise ValueError("Peso fuera del rango existente (0–100)")
        object.__setattr__(self, "weight", weight)
        if self.competency_key is not None:
            identifier(self.competency_key)
        if self.source_header is not None:
            label(self.source_header)
            if header_key(self.source_header) in DERIVED_HEADERS:
                raise ValueError('Una columna derivada no puede mapearse como criterio de entrada')
        if self.legacy_component_id is not None:
            UUID(self.legacy_component_id)


@dataclass(frozen=True)
class Formula:
    key: str
    expression: str

    def __post_init__(self):
        identifier(self.key)


@dataclass(frozen=True)
class Configuration:
    course_id: str
    period_id: str
    competencies: tuple[Competency, ...]
    criteria: tuple[Criterion, ...]
    formulas: tuple[Formula, ...]
    template_id: str = "custom_v1"
    final_formula: str = "pf"

    def __post_init__(self):
        object.__setattr__(self, "course_id", str(UUID(self.course_id)))
        object.__setattr__(self, "period_id", str(UUID(self.period_id)))
        for field in ("competencies", "criteria", "formulas"):
            object.__setattr__(self, field, tuple(getattr(self, field)))
        if not 1 <= len(self.criteria) <= 64 or len(self.competencies) > 32:
            raise ValueError("Cantidad de criterios/competencias fuera del límite")
        if not 1 <= len(self.formulas) <= 32:
            raise ValueError("Se requieren entre una y 32 fórmulas")
        identifier(self.template_id)
        identifiers = [c.key for c in self.criteria] + [f.key for f in self.formulas]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Identificadores duplicados de criterio o fórmula")
        competencies = {c.key: c for c in self.competencies}
        if len(competencies) != len(self.competencies):
            raise ValueError("Competencias duplicadas")
        orders = set()
        headers = set()
        for criterion in self.criteria:
            if (criterion.block, criterion.position) in orders:
                raise ValueError("Orden de criterios duplicado dentro del bloque")
            orders.add((criterion.block, criterion.position))
            if criterion.competency_key:
                parent = competencies.get(criterion.competency_key)
                if parent is None or (criterion.is_active and not parent.is_active):
                    raise ValueError("Competencia inexistente o desactivada para criterio activo")
            if criterion.is_active and criterion.source_header:
                header = (criterion.block, header_key(criterion.source_header))
                if header in headers:
                    raise ValueError("Encabezado ambiguo dentro del mismo bloque")
                headers.add(header)
        if len({c.position for c in self.competencies}) != len(self.competencies):
            raise ValueError("Orden de competencias duplicado")
        for block in (1, 2):
            active = [c for c in self.criteria if c.block == block and c.is_active]
            if not active or sum(c.weight for c in active) <= 0:
                raise ValueError("Cada bloque exige al menos un criterio con peso positivo")
        if self.final_formula not in {f.key for f in self.formulas}:
            raise ValueError("Fórmula final inexistente")
        formula_order(self)

    def document(self) -> dict:
        result = asdict(self)
        for criterion in result["criteria"]:
            weight = format(criterion["weight"], "f")
            criterion["weight"] = weight.rstrip("0").rstrip(".") if "." in weight else weight
        result.update(schema_version=1, formula_language="paideia_numeric_v1",
                      weight_mode="relative_legacy", block_weeks=4, bimester_weeks=8)
        return result

    def canonical(self) -> str:
        return json.dumps(self.document(), sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"))

    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()


def from_document(document: dict) -> Configuration:
    # Refuse to silently drop unknown future fields or reinterpret newer versions.
    metadata = {"schema_version": 1, "formula_language": "paideia_numeric_v1",
                "weight_mode": "relative_legacy", "block_weeks": 4, "bimester_weeks": 8}
    if any(document.get(key) != value for key, value in metadata.items()):
        raise ValueError("Versión o política de configuración no soportada")
    body = {key: value for key, value in document.items() if key not in metadata}
    for field, maximum in [('competencies', 32), ('criteria', 64), ('formulas', 32)]:
        if not isinstance(body.get(field), (list, tuple)) or len(body[field]) > maximum:
            raise ValueError('Documento demasiado grande o con estructura inválida')
    body["competencies"] = tuple(Competency(**value) for value in body["competencies"])
    body["criteria"] = tuple(Criterion(**value) for value in body["criteria"])
    body["formulas"] = tuple(Formula(**value) for value in body["formulas"])
    return Configuration(**body)


def formula_order(config: Configuration) -> tuple[str, ...]:
    active = {c.key for c in config.criteria if c.is_active}
    formulas = {f.key: f for f in config.formulas}
    dependencies = {key: set(parse(f.expression, active | formulas.keys())[1]) - active
                    for key, f in formulas.items()}
    ordered = []
    while dependencies:
        ready = sorted(key for key, refs in dependencies.items() if not refs)
        if not ready:
            raise FormulaError("Ciclo entre fórmulas")
        ordered.extend(ready)
        for key in ready:
            dependencies.pop(key)
        for refs in dependencies.values():
            refs.difference_update(ready)
    return tuple(ordered)


def preview(config: Configuration, scores: dict) -> dict:
    active = {c.key: c for c in config.criteria if c.is_active}
    if set(scores) - active.keys():
        raise ValueError("Notas con criterios desconocidos o inactivos")
    values = {}
    for key in active:
        value = scores.get(key)
        if value is not None:
            value = number(value)
            if not 0 <= value <= 20:
                raise ValueError("La nota debe estar entre 0 y 20")
        values[key] = value
    weighted, warnings = {}, []
    for block in (1, 2):
        criteria = [c for c in active.values() if c.block == block and c.weight > 0]
        missing = [c.key for c in criteria if values[c.key] is None and not c.is_optional]
        available = [c for c in criteria if values[c.key] is not None]
        weighted[str(block)] = None
        if missing:
            warnings.append({"block": block, "missing_required": missing})
        elif available:
            weighted[str(block)] = float(sum(values[c.key] * c.weight for c in available)
                                        / sum(c.weight for c in available))
    formulas = {f.key: f for f in config.formulas}
    for key in formula_order(config):
        value = evaluate(formulas[key].expression, values)
        if value is not None and not 0 <= value <= 20:
            raise FormulaError("Resultado de evaluación fuera de la escala 0–20")
        values[key] = value
    final = values[config.final_formula]
    if warnings:
        # A custom expression can omit an input; do not hide missing required criteria.
        values[config.final_formula] = final = None
    return {"weighted_blocks": weighted, "formula_results": {
        key: float(values[key]) if values[key] is not None else None for key in formulas},
        "literal": literal_grade(float(final)) if final is not None else None,
        "warnings": warnings, "configuration_fingerprint": config.fingerprint(),
        "preview_only": True}


def institutional_template(course_id: str, period_id: str) -> Configuration:
    # Only names/formulas observed in the anonymous Excel; no invented competencies.
    headers = [("actitud", "ACTITUD ANTE EL AREA", "Actitud ante el área"),
               ("cuaderno", "CUADERNO", "Cuaderno"),
               ("modulo", "MODULO", "Módulo"),
               ("exposicion", "EXPOSICION-TRABAJOS", "Exposición-Trabajos"),
               ("evaluacion", "EVALUACION", "Evaluación")]
    criteria, formulas = [], []
    for block in (1, 2):
        keys = []
        for order, (key, header, name) in enumerate(headers):
            key = f"b{block}_{key}"
            keys.append(key)
            criteria.append(Criterion(key, name, block, order, source_header=header))
        formulas.append(Formula(f"mes_{block}", f"ROUND(SUM({','.join(keys)})/5,1)"))
    formulas.append(Formula("pf", "ROUND(MEAN(mes_1,mes_2),1)"))
    return Configuration(course_id, period_id, (), tuple(criteria), tuple(formulas),
                         template_id="institutional_v1")


def source_criterion(config: Configuration, block: int, header: str) -> Criterion | None:
    matches = [c for c in config.criteria if c.is_active and c.block == block
               and c.source_header and header_key(c.source_header) == header_key(header)]
    if len(matches) > 1:
        raise ValueError('Correspondencia de criterio ambigua')
    return matches[0] if matches else None


def reorder_criteria(config: Configuration, block: int, keys: list[str]) -> Configuration:
    current = {c.key for c in config.criteria if c.block == block}
    if set(keys) != current or len(keys) != len(current):
        raise ValueError("El nuevo orden debe incluir todos los criterios del bloque")
    positions = {key: index for index, key in enumerate(keys)}
    return replace(config, template_id="custom_v1", criteria=tuple(
        replace(c, position=positions[c.key]) if c.block == block else c for c in config.criteria))


def from_legacy_components(course_id: str, period_id: str, components: list[dict]) -> Configuration:
    """Copy all existing components, including additional/inactive/optional ones.

    This does not write or replace the original course components or their IDs.
    Formula changes remain explicit; this initial conversion uses current relative weights.
    """
    if not 1 <= len(components) <= 32:
        raise ValueError('Conversión limitada a 32 componentes')
    criteria, formulas, seen = [], [], set()
    for block in (1, 2):
        terms, weights = [], []
        for order, component in enumerate(components):
            component_id = str(UUID(str(component['id'])))
            if block == 1:
                if component_id in seen:
                    raise ValueError('Componente duplicado')
                seen.add(component_id)
            criterion = Criterion(
                key=f'c_{UUID(component_id).hex}_b{block}', name=component['name'],
                block=block, position=order, weight=component['weight'],
                is_active=component.get('is_active', True),
                is_optional=component.get('is_optional', False),
                source_header=(component['name'] if header_key(component['name'])
                               not in DERIVED_HEADERS else None),
                legacy_component_id=component_id)
            criteria.append(criterion)
            if criterion.is_active and criterion.weight > 0:
                weights.append(criterion.weight)
                terms.append(f'{criterion.key}*{criterion.weight}')
        if not terms:
            raise ValueError('No hay componentes activos con peso positivo')
        formulas.append(Formula(f'mes_{block}', f"SUM({','.join(terms)})/{sum(weights)}"))
    formulas.append(Formula('pf', 'MEAN(mes_1,mes_2)'))
    return Configuration(course_id, period_id, (), tuple(criteria), tuple(formulas),
                         template_id='legacy_components_v1')


@dataclass(frozen=True)
class Revision:
    id: str
    course_id: str
    period_id: str
    number: int
    previous_id: str | None
    actor_id: str
    reason: str
    created_at: str
    content: str
    fingerprint: str

    def __post_init__(self):
        for value in (self.id, self.course_id, self.period_id, self.actor_id):
            UUID(value)
        if self.previous_id is not None:
            UUID(self.previous_id)
        if type(self.number) is not int or self.number < 1:
            raise ValueError('Número de revisión inválido')
        label(self.reason, 500)
        created = datetime.fromisoformat(self.created_at)
        if created.tzinfo is None:
            raise ValueError('La revisión requiere fecha con zona horaria')

    def configuration(self) -> Configuration:
        config = from_document(json.loads(self.content))
        if config.fingerprint() != self.fingerprint:
            raise ValueError("Contenido histórico alterado")
        if (config.course_id, config.period_id) != (self.course_id, self.period_id):
            raise ValueError('Ámbito histórico inconsistente')
        return config


def next_revision(config: Configuration, actor_id: str, reason: str,
                  previous: Revision | None = None,
                  expected_previous_id: str | None = None) -> Revision:
    UUID(actor_id)
    label(reason, 500)
    if expected_previous_id != (previous.id if previous else None):
        raise ValueError("Versión obsoleta; vuelve a revisar los cambios")
    if previous:
        previous.configuration()
        if (previous.course_id, previous.period_id) != (config.course_id, config.period_id):
            raise ValueError("Una revisión no puede cambiar de curso o periodo")
        if previous.fingerprint == config.fingerprint():
            return previous
    return Revision(str(uuid4()), config.course_id, config.period_id,
                    previous.number + 1 if previous else 1, previous.id if previous else None,
                    actor_id, reason.strip(), datetime.now(timezone.utc).isoformat(),
                    config.canonical(), config.fingerprint())
