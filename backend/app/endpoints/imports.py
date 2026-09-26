from datetime import datetime
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
import pandas as pd
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import AcademicPeriod, Course, GradeRecord
from app.models.student import Student
from app.models.user import User

router = APIRouter()


def _read_frame(filename: str, content: bytes) -> pd.DataFrame:
    return pd.read_csv(BytesIO(content)) if filename.lower().endswith(".csv") else pd.read_excel(BytesIO(content))


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
    return {"columns": list(frame.columns), "rows": frame.head(50).to_dict(orient="records"), "total": len(frame), "errors": errors}


@router.post("/students")
async def import_students(file: UploadFile = File(...), db: Session = Depends(get_db), _user: User = Depends(require_roles("admin", "coordinator"))) -> dict[str, int]:
    content = await file.read()
    try:
        frame = _read_frame(file.filename or "", content).fillna("")
    except Exception as error:
        raise HTTPException(status_code=422, detail=f"No se pudo leer el archivo: {error}") from error
    errors = [{"row": int(index) + 2, "error": "Código, nombres y apellidos son obligatorios"} for index, row in frame.iterrows() if not str(row.get("student_code", "")).strip() or not str(row.get("first_name", "")).strip() or not str(row.get("last_name", "")).strip()]
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    for row in frame.to_dict(orient="records"):
        db.add(Student(student_code=str(row["student_code"]), first_name=str(row["first_name"]), last_name=str(row["last_name"])))
    try:
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Importación revertida: {error}") from error
    return {"imported": len(frame)}


@router.post("/grades/preview")
async def preview_grade_import(file: UploadFile = File(...), _user: User = Depends(require_roles("admin", "teacher", "coordinator"))) -> dict:
    if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV o Excel")
    content = await file.read()
    try:
        frame = _read_frame(file.filename, content).fillna("")
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
        try:
            score = float(row.get("score", ""))
            if not 0 <= score <= 20:
                raise ValueError
        except (TypeError, ValueError):
            errors.append({"row": int(index) + 2, "error": "La nota debe estar entre 0 y 20"})
    return {"columns": list(frame.columns), "rows": frame.head(50).to_dict(orient="records"), "total": len(frame), "errors": errors}


@router.post("/grades")
async def import_grades(
    file: UploadFile = File(...),
    course_id: UUID | None = Query(default=None),
    period_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "teacher", "coordinator")),
) -> dict[str, int]:
    if course_id is None or period_id is None:
        raise HTTPException(status_code=400, detail="course_id y period_id son obligatorios")
    if not db.get(Course, course_id):
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    if not db.get(AcademicPeriod, period_id):
        raise HTTPException(status_code=404, detail="Periodo no encontrado")

    content = await file.read()
    try:
        frame = _read_frame(file.filename or "", content).fillna("")
    except Exception as error:
        raise HTTPException(status_code=422, detail=f"No se pudo leer el archivo: {error}") from error
    required = {"student_code", "score"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise HTTPException(status_code=422, detail={"missing_columns": missing})

    imported = 0
    for row in frame.to_dict(orient="records"):
        student_code = str(row.get("student_code", "")).strip()
        if not student_code:
            continue
        student = db.scalar(db.query(Student).filter(Student.student_code == student_code))
        if student is None:
            raise HTTPException(status_code=404, detail=f"Estudiante no encontrado: {student_code}")
        try:
            score = float(row.get("score", ""))
        except (TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail=f"Nota inválida para {student_code}: {row.get('score')}") from error
        if not 0 <= score <= 20:
            raise HTTPException(status_code=422, detail=f"La nota para {student_code} debe estar entre 0 y 20")
        record = GradeRecord(
            student_id=student.id,
            course_id=course_id,
            period_id=period_id,
            evaluation_name=str(row.get("evaluation_name", "Evaluación")).strip() or "Evaluación",
            evaluation_type=str(row.get("evaluation_type", "Tarea")).strip() or "Tarea",
            assessment_date=pd.to_datetime(row.get("assessment_date") or datetime.now()).date(),
            score=score,
            qualitative_note=str(row.get("qualitative_note", "")).strip() or None,
        )
        db.add(record)
        imported += 1
    db.commit()
    return {"imported": imported}
