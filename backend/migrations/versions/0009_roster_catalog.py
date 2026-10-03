"""support source roster values and catalog reconciliation

Revision ID: 0009_roster_catalog
Revises: 0008_roster_fields
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_roster_catalog"
down_revision: str | None = "0008_roster_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("students", "student_code", existing_type=sa.String(50), nullable=True)
    op.alter_column("courses", "code", existing_type=sa.String(40), nullable=True)
    op.add_column("grades", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("sections", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("sections", "is_active")
    op.drop_column("grades", "is_active")
    op.alter_column("courses", "code", existing_type=sa.String(40), nullable=False)
    op.alter_column("students", "student_code", existing_type=sa.String(50), nullable=False)
