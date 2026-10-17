"""Trace imported/synthetic evidence and retain superseded records without double counting."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0020_grade_provenance"
down_revision = "0019_historical_grades"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "grade_records",
        sa.Column("data_origin", sa.String(16), nullable=False, server_default="recorded"),
    )
    op.add_column("grade_records", sa.Column("academic_month", sa.Integer(), nullable=True))
    op.add_column("grade_records", sa.Column("source_reference", sa.String(255), nullable=True))
    op.add_column(
        "grade_records", sa.Column("superseded_by_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_grade_superseded",
        "grade_records",
        "grade_records",
        ["superseded_by_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_grade_records_superseded_by_id", "grade_records", ["superseded_by_id"])
    op.create_check_constraint(
        "grade_data_origin", "grade_records", "data_origin IN ('recorded','excel','synthetic')"
    )
    op.create_check_constraint(
        "grade_academic_month",
        "grade_records",
        "academic_month IS NULL OR academic_month BETWEEN 1 AND 12",
    )


def downgrade():
    connection = op.get_bind()
    if connection.scalar(
        sa.text(
            "SELECT count(*) FROM grade_records WHERE data_origin != 'recorded' "
            "OR academic_month IS NOT NULL OR superseded_by_id IS NOT NULL"
        )
    ):
        raise RuntimeError("Provenance is in use; downgrade would discard academic evidence")
    op.drop_constraint("grade_academic_month", "grade_records", type_="check")
    op.drop_constraint("grade_data_origin", "grade_records", type_="check")
    op.drop_index("ix_grade_records_superseded_by_id", table_name="grade_records")
    op.drop_constraint("fk_grade_superseded", "grade_records", type_="foreignkey")
    for column in ("superseded_by_id", "source_reference", "academic_month", "data_origin"):
        op.drop_column("grade_records", column)
