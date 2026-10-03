"""configure assessment components and weights per course

Revision ID: 0005_course_components
Revises: 0004_follow_up_attribution
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_course_components"
down_revision: str | None = "0004_follow_up_attribution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "course_assessment_components",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_optional", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("course_id", "name", name="uq_course_assessment_component_name"),
    )
    op.add_column("grade_records", sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_grade_records_component_id_course_assessment_components",
        "grade_records",
        "course_assessment_components",
        ["component_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_grade_records_component_id_course_assessment_components", "grade_records", type_="foreignkey")
    op.drop_column("grade_records", "component_id")
    op.drop_table("course_assessment_components")