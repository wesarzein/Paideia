import uuid
from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grades.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
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


class GradeRecord(Base):
    __tablename__ = "grade_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    period_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academic_periods.id"), nullable=False)
    score: Mapped[float] = mapped_column(nullable=False)
    qualitative_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
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
