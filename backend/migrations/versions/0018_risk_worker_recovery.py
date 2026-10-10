"""Bind candidate publication to a specific worker claim."""

import sqlalchemy as sa
from alembic import op

revision = "0018_risk_worker_recovery"
down_revision = "0017_academic_change_history"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("risk_model_runs", sa.Column("worker_token", sa.UUID()))
    op.add_column("risk_model_runs", sa.Column("started_at", sa.DateTime(timezone=True)))


def downgrade():
    op.drop_column("risk_model_runs", "started_at")
    op.drop_column("risk_model_runs", "worker_token")
