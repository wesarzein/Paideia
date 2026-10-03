"""add follow-up author and category

Revision ID: 0004_follow_up_attribution
Revises: 0003_schema_convergence
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_follow_up_attribution"
down_revision: str | None = "0003_schema_convergence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "follow_ups",
        sa.Column("recorded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "follow_ups",
        sa.Column("category", sa.String(40), nullable=False, server_default="OBSERVATION"),
    )
    op.create_foreign_key(
        "fk_follow_ups_recorded_by_id_users",
        "follow_ups",
        "users",
        ["recorded_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_follow_ups_recorded_by_id_users", "follow_ups", type_="foreignkey")
    op.drop_column("follow_ups", "category")
    op.drop_column("follow_ups", "recorded_by_id")