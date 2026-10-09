"""Preserve user identities while enabling account deactivation."""

import sqlalchemy as sa
from alembic import op

revision = "0015_user_account_status"
down_revision = "0014_evaluation_configuration_revisions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())
    )


def downgrade():
    op.drop_column("users", "is_active")
