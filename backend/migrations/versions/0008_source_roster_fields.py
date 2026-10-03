"""allow source roster records without invented codes

Revision ID: 0008_roster_fields
Revises: 0007_course_active
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_roster_fields"
down_revision: str | None = "0007_course_active"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("students", "student_code", existing_type=sa.String(50), nullable=True)
    op.alter_column("courses", "code", existing_type=sa.String(40), nullable=True)
    op.add_column("course_assignments", sa.Column("teacher_name", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("course_assignments", "teacher_name")
    op.alter_column("courses", "code", existing_type=sa.String(40), nullable=False)
    op.alter_column("students", "student_code", existing_type=sa.String(50), nullable=False)
