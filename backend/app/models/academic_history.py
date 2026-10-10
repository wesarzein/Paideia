import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AcademicChangeHistory(Base):
    __tablename__ = "academic_change_history"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity: Mapped[str] = mapped_column(String(40))
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    course_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    operation: Mapped[str] = mapped_column(String(10))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_role: Mapped[str | None] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(20))
    authorization: Mapped[dict | None] = mapped_column(JSON)
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
