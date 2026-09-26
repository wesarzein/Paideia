"""add evaluation fields to grade records

Revision ID: 0002_grade_evaluation_fields
Revises: 0001_initial_structure
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_grade_evaluation_fields"
down_revision: str | None = "0001_initial_structure"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "grade_records",
        sa.Column("evaluation_name", sa.String(120), nullable=False, server_default="Evaluación"),
    )
    op.add_column(
        "grade_records",
        sa.Column("evaluation_type", sa.String(50), nullable=False, server_default="Tarea"),
    )
    op.add_column(
        "grade_records",
        sa.Column("assessment_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
    )


def downgrade() -> None:
    op.drop_column("grade_records", "assessment_date")
    op.drop_column("grade_records", "evaluation_type")
    op.drop_column("grade_records", "evaluation_name")