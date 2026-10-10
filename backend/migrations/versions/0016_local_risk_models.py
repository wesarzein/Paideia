"""Add experimental model lineage, approval and serialized deployments."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0016_local_risk_models"
down_revision = "0015_user_account_status"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "risk_model_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("dataset_schema", sa.String(63), unique=True, nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column("error_code", sa.String(80)),
        sa.Column("created_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("mode IN ('demonstration', 'institutional')", name="risk_run_mode"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'candidate', 'approved', 'failed')",
            name="risk_run_status",
        ),
    )
    op.create_table(
        "risk_model_deployments",
        sa.Column("mode", sa.String(20), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("risk_model_runs.id")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "mode IN ('demonstration', 'institutional')", name="risk_deployment_mode"
        ),
    )
    op.bulk_insert(
        sa.table(
            "risk_model_deployments", sa.column("mode", sa.String), sa.column("version", sa.Integer)
        ),
        [{"mode": "demonstration", "version": 0}, {"mode": "institutional", "version": 0}],
    )
    op.create_table(
        "risk_model_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("risk_model_runs.id")),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("risk_model_events")
    op.drop_table("risk_model_deployments")
    op.drop_table("risk_model_runs")
