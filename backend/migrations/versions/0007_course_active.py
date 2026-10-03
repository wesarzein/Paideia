"""soft activate and deactivate courses

Revision ID: 0007_course_active
Revises: 0006_course_assignments
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_course_active"
down_revision: str | None = "0006_course_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("courses", "is_active")