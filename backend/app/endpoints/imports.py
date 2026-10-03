from datetime import date
from io import BytesIO
from typing import Any
import re
import unicodedata
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
import pandas as pd
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AcademicPeriod, Course, Grade, GradeRecord, Section
from app.models.student import Student
from app.models.user import User
from app.services.academic_access import ensure_student_course_access
from app.services.evidence_types import normalize_evidence_type
from app.services.student_codes import format_student_code, student_code_prefix

router = APIRouter()


class StudentRowsImport(BaseModel):
    grade_id: UUID
    section_id: UUID
    rows: list[dict[str, Any]]


class GradeRowsImport(BaseModel):
    course_id: UUID
    period_id: UUID
    rows: list[dict[str, Any]]


def _read_frame(filename: str, content: bytes) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        return _canonicalize_frame(pd.read_csv(BytesIO(content)))
    content_stream = BytesIO(content)
    frame = pd.read_excel(content_stream)
    normalized = _canonicalize_frame(frame)
    if "student_code" in normalized.columns:
        return normalized
    raw = pd.read_excel(BytesIO(content), header=None).fillna("")
    header_row = _find_roster_header(raw)
    if header_row is None:
        return normalized
    header_end = header_row
    if header_row + 1 < len(raw) and _has_component_header(raw.iloc[header_row + 1].tolist()):
        header_end += 1
    merged_month_rows = []
    for row_index in range(header_row):
        values = raw.iloc[row_index].tolist()
        if any(_header_key(value) in {"1mes", "2mes", "3mes", "4mes", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "septiembre", "octubre", "noviembre", "diciembre"} for value in values):
            forward = list(values)
            current = ""
            for column_index in range(2, len(forward)):
                if str(forward[column_index]).strip():
                    current = str(forward[column_index]).strip()
                elif current:
                    forward[column_index] = current
            merged_month_rows.append(forward)
    headers = []
    for column_index in range(raw.shape[1]):
        parts = [str(raw.iat[header_row, column_index]).strip()]
        parts.extend(str(raw.iat[header_end, column_index]).strip() for _ in [0] if header_end > header_row)
        if column_index >= 2:
            parts = [*(str(row[column_index]).strip() for row in merged_month_rows), *parts]
        unique = list(dict.fromkeys(part for part in parts if part and not part.lower().startswith("unnamed")))
        headers.append(" ".join(unique) or f"column_{column_index + 1}")
    body = raw.iloc[header_end + 1:].copy()
    body.columns = headers
    return _canonicalize_frame(body.reset_index(drop=True))


def _find_roster_header(frame: pd.DataFrame) -> int | None:
    code_headers = {"studentcode", "codigo", "codigoalumno", "codigodelalumno", "codigoestudiante", "codalumno", "codestudiante"}
    name_headers = {"nombreyapellidos", "apellidosynombres", "nombrecompleto", "alumno", "estudiante", "nombres", "apellidos"}
    for row_index in range(min(20, len(frame))):
        keys = {_header_key(value) for value in frame.iloc[row_index].tolist() if str(value).strip()}
        if keys.intersection(code_headers) and keys.intersection(name_headers):
            return row_index
    return None


def _has_component_header(values: list[object]) -> bool:
    keys = [_header_key(value) for value in values]
    return any(any(token in key for token in ("actitud", "cuaderno", "modulo", "exposicion", "trabajos", "evaluacion", "examen", "promediomensual")) for key in keys)


def _header_key(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", normalized)


def _canonicalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "student_code": {"studentcode", "codigo", "codigoalumno", "codigodelalumno", "codigoestudiante", "codalumno", "codestudiante"},
        "full_name": {"nombreyapellidos", "apellidosynombres", "nombrecompleto", "alumno", "estudiante"},
        "first_name": {"nombres", "firstname", "name"},
        "last_name": {"apellidos", "lastname", "surname"},
        "score": {"nota", "calificacion", "puntaje", "score"},
        "evaluation_name": {"evaluacion", "nombreevaluacion", "actividad"},
        "evaluation_type": {"tipo", "componente", "componentedeevaluacion"},
        "assessment_date": {"fecha", "fechadeevaluacion", "assessmentdate"},
        "qualitative_note": {"observacion", "comentario", "seguimiento", "qualitativenote"},
    }
    reverse = {alias: canonical for canonical, names in aliases.items() for alias in names}
    rename = {column: reverse[_header_key(column)] for column in frame.columns if _header_key(column) in reverse}
    normalized = frame.rename(columns=rename).copy()
    if "full_name" in normalized.columns:
        names = normalized["full_name"].fillna("").astype(str).str.split(",", n=1, expand=True)
        if names.shape[1] == 2:
            if "last_name" not in normalized.columns:
                normalized["last_name"] = names[0].str.strip()
            if "first_name" not in normalized.columns:
                normalized["first_name"] = names[1].str.strip()
    return normalized


def _date_for_month(month_number: str, period: AcademicPeriod | None) -> str:
    if period is None:
        return ""
    candidates = [date(year, int(month_number), 1) for year in range(period.starts_on.year, period.ends_on.year + 1)]
    valid = [candidate for candidate in candidates if period.starts_on <= candidate <= period.ends_on]
    return valid[0].isoformat() if len(valid) == 1 else ""


def _flatten_grade_frame(frame: pd.DataFrame, period: AcademicPeriod | None = None) -> pd.DataFrame:
    frame = _canonicalize_frame(frame)
    if "score" in frame.columns:
        return frame
    code_column = "student_code" if "student_code" in frame.columns else None
    if code_column is None:
        return frame
    components = []
    component_tokens = {
        "actitud": "Actitud ante el área",
        "cuaderno": "Cuaderno",
        "modulo": "Módulo",
        "exposicion": "Exposición-Trabajos",
        "trabajos": "Exposición-Trabajos",
        "evaluacion": "Evaluación",
        "examen": "Evaluación",
    }
    for column in frame.columns:
        key = _header_key(column)
        if "promediomensual" in key or column in {"student_code", "first_name", "last_name", "full_name"}:
            continue
        component = next((label for token, label in component_tokens.items() if token in key), None)
        if component:
            components.append((column, key, component))
    if not components:
        return frame
    month_names = {"enero": "01", "febrero": "02", "marzo": "03", "abril": "04", "mayo": "05", "junio": "06", "julio": "07", "agosto": "08", "setiembre": "09", "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"}
    rows = []
    for _, source in frame.iterrows():
        code = str(source.get("student_code", "")).strip()
        if not code:
            continue
        for column, key, component in components:
            value = source.get(column)
            if pd.isna(value) or str(value).strip() == "":
                continue
            month_match = next(((name, number) for name, number in month_names.items() if name in key), None)
            month_index = re.search(r"(?:mes)?(1[0-2]|[1-9])mes?", key)
            month_label = month_match[0].title() if month_match else f"Mes {month_index.group(1)}" if month_index else ""
            month_number = month_match[1] if month_match else month_index.group(1) if month_index else None
            assessment_date = _date_for_month(month_number, period) if month_number else ""
            rows.append({"student_code": code, "score": value, "evaluation_name": month_label or "Evaluación", "evaluation_type": component, "assessment_date": assessment_date, "qualitative_note": ""})
    return pd.DataFrame(rows, columns=["student_code", "score", "evaluation_name", "evaluation_type", "assessment_date", "qualitative_note"])


@router.post("/preview")
async def preview_students(file: UploadFile = File(...), _user: User = Depends(require_roles("admin", "coordinator"))) -> dict:
    if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV o Excel")
    content = await file.read()
    try:
        frame = _read_frame(file.filename, content)
    except Exception as error:
        raise HTTPException(status_code=422, detail=f"No se pudo leer el archivo: {error}") from error
    required = {"student_code", "first_name", "last_name"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise HTTPException(status_code=422, detail={"missing_columns": missing})
    frame = frame.fillna("")
    errors = []
    for index, row in frame.iterrows():
        if not str(row["student_code"]).strip() or not str(row["first_name"]).strip() or not str(row["last_name"]).strip():
            errors.append({"row": int(index) + 2, "error": "Código, nombres y apellidos son obligatorios"})
    return {"columns": list(frame.columns), "rows": frame.to_dict(orient="records"), "total": len(frame), "errors": errors}


@router.post("/students/commit")
def commit_student_rows(payload: StudentRowsImport, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "coordinator"))) -> dict[str, int]:
    grade = db.get(Grade, payload.grade_id)
    section = db.get(Section, payload.section_id)
    if grade is None or section is None or section.grade_id != grade.id:
        raise HTTPException(status_code=422, detail="Grado y sección no corresponden")
    errors = []
    normalized = []
    prefix = student_code_prefix(grade, section)
    existing_codes = db.scalars(select(Student.student_code).where(Student.student_code.like(f"{prefix}%"))).all()
    next_order = max((int(code[len(prefix):]) for code in existing_codes if code and code[len(prefix):].isdigit()), default=0) + 1
    for index, row in enumerate(payload.rows, 1):
        first_name = str(row.get("first_name", "")).strip()
        last_name = str(row.get("last_name", "")).strip()
        if not first_name or not last_name:
            errors.append({"row": index, "error": "Nombres y apellidos son obligatorios"})
            continue
        code = format_student_code(grade, section, next_order)
        next_order += 1
        normalized.append(Student(student_code=code, first_name=first_name, last_name=last_name, grade_id=grade.id, section_id=section.id))
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors, "rejected": len(errors)})
    try:
        db.add_all(normalized)
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Importación revertida completamente: {error}") from error
    return {"processed": len(payload.rows), "imported": len(normalized), "rejected": 0}


@router.post("/grades/preview")
async def preview_grade_import(file: UploadFile = File(...), period_id: UUID | None = Query(default=None), db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "teacher", "coordinator"))) -> dict:
    if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV o Excel")
    content = await file.read()
    period = db.get(AcademicPeriod, period_id) if period_id else None
    if period_id and period is None:
        raise HTTPException(status_code=404, detail="Periodo no encontrado")
    try:
        frame = _flatten_grade_frame(_read_frame(file.filename, content), period).fillna("")
    except Exception as error:
        raise HTTPException(status_code=422, detail=f"No se pudo leer el archivo: {error}") from error
    required = {"student_code", "score"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise HTTPException(status_code=422, detail={"missing_columns": missing})
    errors = []
    for index, row in frame.iterrows():
        if not str(row.get("student_code", "")).strip():
            errors.append({"row": int(index) + 2, "error": "Falta student_code"})
        evidence_type = str(row.get("evaluation_type", "")).strip()
        if evidence_type:
            try:
                frame.at[index, "evaluation_type"] = normalize_evidence_type(evidence_type)
            except ValueError as error:
                errors.append({"row": int(index) + 2, "error": str(error)})
        try:
            score = float(row.get("score", ""))
            if not 0 <= score <= 20:
                raise ValueError
        except (TypeError, ValueError):
            errors.append({"row": int(index) + 2, "error": "La nota debe estar entre 0 y 20"})
    return {"columns": list(frame.columns), "rows": frame.to_dict(orient="records"), "total": len(frame), "errors": errors}


@router.post("/grades/commit")
def commit_grade_rows(payload: GradeRowsImport, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "teacher", "coordinator"))) -> dict[str, int]:
    course = db.get(Course, payload.course_id)
    period = db.get(AcademicPeriod, payload.period_id)
    if course is None or period is None:
        raise HTTPException(status_code=404, detail="Curso o periodo no encontrado")
    if not course.is_active:
        raise HTTPException(status_code=409, detail="No se pueden importar notas a un curso inactivo")

    prepared: list[GradeRecord] = []
    errors = []
    for index, row in enumerate(payload.rows, 1):
        code = str(row.get("student_code", "")).strip()
        student = db.scalar(select(Student).where(Student.student_code == code)) if code else None
        if student is None:
            errors.append({"row": index, "error": f"Estudiante no encontrado: {code or '(sin código)'}"})
            continue
        try:
            ensure_student_course_access(db, user, student, payload.course_id, payload.period_id)
        except HTTPException as error:
            errors.append({"row": index, "error": error.detail})
            continue
        try:
            score = float(row.get("score", ""))
        except (TypeError, ValueError) as error:
            errors.append({"row": index, "error": f"Nota inválida: {row.get('score')}"})
            continue
        if not 0 <= score <= 20:
            errors.append({"row": index, "error": "La nota debe estar entre 0 y 20"})
            continue
        assessment_date = row.get("assessment_date")
        if not assessment_date:
            normalized_month = _header_key(row.get("evaluation_name", ""))
            month_number = next((number for name, number in {"enero": "01", "febrero": "02", "marzo": "03", "abril": "04", "mayo": "05", "junio": "06", "julio": "07", "agosto": "08", "setiembre": "09", "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"}.items() if name in normalized_month), None)
            assessment_date = _date_for_month(month_number, period) if month_number else None
        parsed_date = pd.to_datetime(assessment_date, errors="coerce") if assessment_date else pd.NaT
        if pd.isna(parsed_date):
            errors.append({"row": index, "error": "Fecha ambigua o ausente; asígnala en la vista previa"})
            continue
        parsed_assessment_date = parsed_date.date()
        if not period.starts_on <= parsed_assessment_date <= period.ends_on:
            errors.append({"row": index, "error": "La fecha de evaluación está fuera del periodo seleccionado"})
            continue
        evaluation_type = str(row.get("evaluation_type", "Actitud ante el área")).strip() or "Actitud ante el área"
        try:
            evaluation_type = normalize_evidence_type(evaluation_type)
        except ValueError as error:
            errors.append({"row": index, "error": str(error)})
            continue
        prepared.append(GradeRecord(
            student_id=student.id,
            course_id=payload.course_id,
            period_id=payload.period_id,
            evaluation_name=str(row.get("evaluation_name", "Evaluación")).strip() or "Evaluación",
            evaluation_type=evaluation_type,
            assessment_date=parsed_assessment_date,
            score=score,
            qualitative_note=str(row.get("qualitative_note", "")).strip() or None,
        ))
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors, "rejected": len(errors)})
    try:
        db.add_all(prepared)
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Importación revertida completamente por un conflicto de datos") from error
    return {"processed": len(payload.rows), "imported": len(prepared), "rejected": 0}
