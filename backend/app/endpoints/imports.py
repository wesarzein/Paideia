from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
import pandas as pd
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
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