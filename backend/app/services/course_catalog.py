import hashlib
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import Course


def _key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", normalized)


_COURSE_NAMES = {
    "apverbal": "Aptitud Verbal",
    "aptitudverbal": "Aptitud Verbal",
    "comlinguistica": "Comunicación Lingüística",
    "comunicacionlinguistica": "Comunicación Lingüística",
    "razmat": "Razonamiento Matemático",
    "razmatematico": "Razonamiento Matemático",
    "razonamientomatematico": "Razonamiento Matemático",
    "razverbal": "Razonamiento Verbal",
    "razonamientoverbal": "Razonamiento Verbal",
    "edfisica": "Educación Física",
    "educacionfisica": "Educación Física",
    "edporeltrabajo": "Educación para el Trabajo",
    "educacionporeltrabajo": "Educación para el Trabajo",
    "edporarte": "Educación por el Arte",
    "educacionporelarte": "Educación por el Arte",
    "trigonomet": "Trigonometría",
    "trigonometria": "Trigonometría",
    "com": "Comunicación",
    "comunicacion": "Comunicación",
    "matematica": "Matemática",
}


def canonical_course_name(name: str) -> str:
    clean_name = " ".join(name.strip().split())
    return _COURSE_NAMES.get(_key(clean_name), clean_name)


def generate_course_code(name: str) -> str:
    canonical_name = canonical_course_name(name)
    slug = unicodedata.normalize("NFKD", canonical_name).encode("ascii", "ignore").decode().upper()
    slug = re.sub(r"[^A-Z0-9]+", "-", slug).strip("-")[:20].rstrip("-")
    digest = hashlib.sha256(_key(canonical_name).encode("utf-8")).hexdigest()[:6].upper()
    return f"CUR-{slug}-{digest}"


def unique_course_code(db: Session, name: str) -> str:
    code = generate_course_code(name)
    existing = db.scalar(select(Course.id).where(Course.code == code))
    if existing is None:
        return code

    suffix = 2
    while db.scalar(select(Course.id).where(Course.code == f"{code}-{suffix}")) is not None:
        suffix += 1
    return f"{code}-{suffix}"
