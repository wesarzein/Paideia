from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.academic import CourseAssignment
from app.models.student import Student
from app.models.academic import Grade, Section
from app.schemas.students import StudentCreate, StudentResponse, StudentSummary, StudentUpdate
from app.services.academic_access import ensure_student_view_access
from app.services.student_codes import format_student_code, student_code_prefix

router = APIRouter()


@router.get("", response_model=list[StudentResponse])
def list_students(
    search: str | None = Query(default=None, max_length=100),
    student_status: str | None = Query(default=None, alias="status", max_length=30),
    grade_id: UUID | None = None,
    section_id: UUID | None = None,
    period_id: UUID | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "teacher", "coordinator", "director", "student", "parent")),
) -> list[Student]:
    statement = select(Student)
    if user.role.code == "teacher":
        statement = statement.join(
            CourseAssignment,
            (CourseAssignment.grade_id == Student.grade_id)
            & (CourseAssignment.section_id == Student.section_id),
        ).where(CourseAssignment.teacher_id == user.id).distinct().order_by(
            Student.student_code, Student.last_name, Student.first_name
        )
    elif user.role.code == "student":
        statement = statement.where(Student.student_user_id == user.id).order_by(Student.student_code)
    elif user.role.code == "parent":
        statement = statement.where(Student.parent_user_id == user.id).order_by(Student.student_code)
    else:
        statement = statement.outerjoin(Grade, Student.grade_id == Grade.id).outerjoin(
            Section, Student.section_id == Section.id
        ).order_by(
            Grade.level, Grade.name, Section.name, Student.student_code, Student.last_name, Student.first_name
        )
    if student_status is None:
        statement = statement.where(Student.status == "ACTIVE")
    if search:
        search_term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Student.student_code.ilike(search_term),
                Student.first_name.ilike(search_term),
                Student.last_name.ilike(search_term),
            )
        )
    if student_status:
        statement = statement.where(Student.status == student_status)
    if grade_id:
        statement = statement.where(Student.grade_id == grade_id)
    if section_id:
        statement = statement.where(Student.section_id == section_id)
    return list(db.scalars(statement).all())


@router.get("/summary", response_model=StudentSummary)
def student_summary(db: Session = Depends(get_db), user=Depends(require_roles("admin", "teacher", "coordinator", "director", "student", "parent"))) -> StudentSummary:
    statement = select(Student.id)
    if user.role.code == "teacher":
        statement = statement.join(
            CourseAssignment,
            (CourseAssignment.grade_id == Student.grade_id)
            & (CourseAssignment.section_id == Student.section_id),
        ).where(CourseAssignment.teacher_id == user.id).distinct()
    elif user.role.code == "student":
        statement = statement.where(Student.student_user_id == user.id)
    elif user.role.code == "parent":
        statement = statement.where(Student.parent_user_id == user.id)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    active = db.scalar(select(func.count()).select_from(statement.where(Student.status == "ACTIVE").subquery())) or 0
    return StudentSummary(total=total, active=active, inactive=total - active)


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), _user=Depends(require_roles("admin", "coordinator"))) -> Student:
    data = payload.model_dump()
    if data.get("grade_id") is None or data.get("section_id") is None:
        raise HTTPException(status_code=422, detail="Selecciona grado y sección para generar el código escolar")
    grade = db.get(Grade, data["grade_id"])
    section = db.get(Section, data["section_id"])
    if grade is None or section is None or section.grade_id != grade.id:
        raise HTTPException(status_code=422, detail="La sección seleccionada no pertenece al grado")
    prefix = student_code_prefix(grade, section)
    existing_codes = db.scalars(select(Student.student_code).where(Student.student_code.like(f"{prefix}%"))).all()
    highest_order = max((int(code[len(prefix):]) for code in existing_codes if code and code[len(prefix):].isdigit()), default=0)
    data["student_code"] = format_student_code(grade, section, highest_order + 1)
    student = Student(**data)
    db.add(student)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="El código del estudiante ya existe") from error
    db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: UUID, db: Session = Depends(get_db), user=Depends(require_roles("admin", "teacher", "coordinator", "director", "student", "parent"))) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    ensure_student_view_access(user, student)
    if user.role.code == "teacher" and db.scalar(select(CourseAssignment.id).where(CourseAssignment.grade_id == student.grade_id, CourseAssignment.section_id == student.section_id, CourseAssignment.teacher_id == user.id)) is None:
        raise HTTPException(status_code=403, detail="No tienes acceso a este estudiante")
    return student


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: UUID, payload: StudentUpdate, db: Session = Depends(get_db), _user=Depends(require_roles("admin", "coordinator"))
) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    placement_changed = "grade_id" in payload.model_fields_set or "section_id" in payload.model_fields_set
    if placement_changed:
        grade = db.get(Grade, student.grade_id) if student.grade_id else None
        section = db.get(Section, student.section_id) if student.section_id else None
        if grade is None or section is None or section.grade_id != grade.id:
            raise HTTPException(status_code=422, detail="La sección seleccionada no pertenece al grado")
        prefix = student_code_prefix(grade, section)
        existing_codes = db.scalars(select(Student.student_code).where(Student.student_code.like(f"{prefix}%"), Student.id != student.id)).all()
        highest_order = max((int(code[len(prefix):]) for code in existing_codes if code and code[len(prefix):].isdigit()), default=0)
        student.student_code = format_student_code(grade, section, highest_order + 1)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: UUID, db: Session = Depends(get_db), _user=Depends(require_roles("admin", "coordinator"))) -> None:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    student.status = "INACTIVE"
    db.commit()