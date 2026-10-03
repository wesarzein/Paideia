import re

from app.models.academic import Grade, Section


def student_code_prefix(grade: Grade, section: Section) -> str:
    grade_number = re.sub(r"\D", "", grade.name)
    if not grade_number:
        raise ValueError(f"El grado '{grade.name}' no contiene un número")
    if grade.level.strip().casefold() == "primaria":
        return f"{grade_number}P"
    if grade.level.strip().casefold() == "secundaria":
        section_name = section.name.strip().upper()
        if len(section_name) != 1 or not section_name.isalpha():
            raise ValueError(f"La sección '{section.name}' no es válida para generar el código")
        return f"{grade_number}S{section_name}"
    raise ValueError(f"El nivel '{grade.level}' no permite generar un código escolar")


def format_student_code(grade: Grade, section: Section, order: int) -> str:
    if order < 1:
        raise ValueError("El orden del estudiante debe ser positivo")
    return f"{student_code_prefix(grade, section)}{order:03d}"
