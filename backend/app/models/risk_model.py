import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskModelRun(Base):
    __tablename__ = "risk_model_runs"
    __table_args__ = (
        CheckConstraint("mode IN ('demonstration', 'institutional')", name="risk_run_mode"),
        CheckConstraint(
            "status IN ('queued', 'running', 'candidate', 'approved', 'failed')",
            name="risk_run_status",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    dataset_schema: Mapped[str] = mapped_column(String(63), nullable=False, unique=True)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RiskModelDeployment(Base):
    __tablename__ = "risk_model_deployments"
    __table_args__ = (
        CheckConstraint("mode IN ('demonstration', 'institutional')", name="risk_deployment_mode"),
    )
    mode: Mapped[str] = mapped_column(String(20), primary_key=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("risk_model_runs.id"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RiskModelEvent(Base):
    __tablename__ = "risk_model_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("risk_model_runs.id"), nullable=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
