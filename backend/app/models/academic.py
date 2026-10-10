import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    inspect,
    select,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AcademicPeriod(Base):
    __tablename__ = "academic_periods"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    starts_on: Mapped[datetime] = mapped_column(Date, nullable=False)
    ends_on: Mapped[datetime] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    level: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grades.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    period_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_periods.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CourseAssessmentComponent(Base):
    __tablename__ = "course_assessment_components"
    __table_args__ = (UniqueConstraint("course_id", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CourseAssignment(Base):
    __tablename__ = "course_assignments"
    __table_args__ = (UniqueConstraint("course_id", "section_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    grade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grades.id"), nullable=False)
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sections.id"), nullable=False)
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    teacher_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvaluationConfigurationRevision(Base):
    """Append-only evaluation configuration for one course and academic period."""

    __tablename__ = "evaluation_configuration_revisions"
    __table_args__ = (
        UniqueConstraint(
            "course_id", "period_id", "version", name="uq_evaluation_revision_scope_version"
        ),
        CheckConstraint("version > 0", name="evaluation_revision_positive_version"),
        CheckConstraint(
            "state IN ('draft', 'published')", name="evaluation_revision_state"
        ),
        Index("ix_evaluation_revision_scope", "course_id", "period_id", "version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    period_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("academic_periods.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evaluation_configuration_revisions.id", ondelete="RESTRICT"), nullable=True
    )
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


@event.listens_for(EvaluationConfigurationRevision, "before_update")
@event.listens_for(EvaluationConfigurationRevision, "before_delete")
def preserve_evaluation_revision(_mapper, _connection, _revision):
    raise ValueError("Las revisiones de evaluación son inmutables")


class GradeRecord(Base):
    __tablename__ = "grade_records"
    __table_args__ = (
        CheckConstraint(
            "academic_bimester IS NULL OR academic_bimester > 0",
            name="grade_records_positive_bimester",
        ),
        CheckConstraint(
            "evaluation_block IS NULL OR evaluation_block IN (1, 2)",
            name="grade_records_evaluation_block",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    period_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_periods.id"), nullable=False)
    component_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("course_assessment_components.id"), nullable=True
    )
    academic_bimester: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluation_block: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluation_criterion_key: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    evaluation_name: Mapped[str] = mapped_column(String(120), default="Evaluación", nullable=False)
    evaluation_type: Mapped[str] = mapped_column(String(50), default="Actitud ante el área", nullable=False)
    assessment_date: Mapped[datetime] = mapped_column(Date, nullable=False, default=func.now())
    score: Mapped[float] = mapped_column(nullable=False)
    assessment_weight: Mapped[float] = mapped_column(Float, nullable=False)
    assessment_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    evaluation_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evaluation_configuration_revisions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    qualitative_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


@event.listens_for(GradeRecord, "before_insert")
def capture_assessment_config(_mapper, connection, record):
    """Capture for every ORM writer, including imports; PostgreSQL also enforces this."""
    component = connection.execute(
        select(CourseAssessmentComponent.__table__).where(
            CourseAssessmentComponent.id == record.component_id
        )
    ).mappings().first() if record.component_id else None
    revision = connection.execute(
        select(EvaluationConfigurationRevision.__table__).where(
            EvaluationConfigurationRevision.id == record.evaluation_revision_id
        )
    ).mappings().first() if record.evaluation_revision_id else None
    if record.evaluation_revision_id and revision is None:
        raise ValueError("La revisión de evaluación no existe")
    if revision and (
        revision["state"] != "published"
        or revision["course_id"] != record.course_id
        or revision["period_id"] != record.period_id
    ):
        raise ValueError("La revisión de evaluación no está publicada para este curso y periodo")
    criterion = None
    if revision:
        if (
            record.academic_bimester is None
            or record.academic_bimester < 1
            or record.evaluation_block not in (1, 2)
            or not record.evaluation_criterion_key
        ):
            raise ValueError("La nota configurable requiere bimestre, bloque y criterio")
        criterion = next(
            (
                item
                for item in revision["configuration"].get("criteria", [])
                if item.get("key") == record.evaluation_criterion_key
            ),
            None,
        )
        if (
            criterion is None
            or criterion.get("is_active") is not True
            or criterion.get("block") != record.evaluation_block
        ):
            raise ValueError("El criterio no está activo en el bloque de la revisión publicada")
    record.assessment_weight = (
        float(criterion["weight"])
        if criterion is not None
        else float(component["weight"]) if component else 1.0
    )
    record.assessment_config = {
        "schema_version": 2 if revision else 1,
        "algorithm": "weighted_mean_v1",
        "origin": "record_insert",
        "component_id": str(record.component_id) if record.component_id else None,
        "component_name": (
            criterion["name"] if criterion is not None
            else component["name"] if component else None
        ),
        "is_optional": (
            criterion["is_optional"] if criterion is not None
            else component["is_optional"] if component else None
        ),
        "weight": record.assessment_weight,
        "academic_bimester": record.academic_bimester,
        "evaluation_block": record.evaluation_block,
        "evaluation_criterion_key": record.evaluation_criterion_key,
        "evaluation_revision_id": str(record.evaluation_revision_id) if revision else None,
        "evaluation_revision_version": revision["version"] if revision else None,
        "evaluation_revision_hash": revision["content_hash"] if revision else None,
    }


@event.listens_for(GradeRecord, "before_update")
def preserve_assessment_config(_mapper, _connection, record):
    for field in (
        "assessment_weight",
        "assessment_config",
        "evaluation_revision_id",
        "academic_bimester",
        "evaluation_block",
        "evaluation_criterion_key",
    ):
        if inspect(record).attrs[field].history.has_changes():
            raise ValueError("La configuración histórica de una nota es inmutable")


class GradeRecordIdentity(Base):
    __tablename__ = "grade_record_identities"

    identity_key: Mapped[str] = mapped_column(Text, primary_key=True)
    # NULL reserves ambiguous legacy groups without choosing or deleting a grade.
    grade_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("grade_records.id", ondelete="CASCADE", deferrable=True, initially="DEFERRED"),
        nullable=True,
        index=True,
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    period_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_periods.id"), nullable=False)
    attendance_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    remarks: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
