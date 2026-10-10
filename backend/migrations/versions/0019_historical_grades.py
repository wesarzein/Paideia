"""Separate undated historical bimester records from dated evaluations."""
from alembic import op
import sqlalchemy as sa

revision = "0019_historical_grades"
down_revision = "0018_risk_worker_recovery"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("grade_records", sa.Column("record_kind", sa.String(24), nullable=False,
                                            server_default="evaluation"))
    op.alter_column("grade_records", "assessment_date", nullable=True, server_default=None)
    op.create_check_constraint("grade_records_record_kind", "grade_records",
        "(record_kind = 'evaluation' AND assessment_date IS NOT NULL) OR "
        "(record_kind = 'historical_bimester' AND assessment_date IS NULL "
        "AND academic_bimester IS NOT NULL AND evaluation_block IS NOT NULL "
        "AND component_id IS NULL AND evaluation_revision_id IS NULL)")


def downgrade():
    # Never invent dates for historical records to satisfy an older schema.
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM grade_records WHERE assessment_date IS NULL")):
        raise RuntimeError("Historical grades must be preserved; downgrade is unavailable")
    op.drop_constraint("grade_records_record_kind", "grade_records", type_="check")
    op.alter_column("grade_records", "assessment_date", nullable=False)
    op.drop_column("grade_records", "record_kind")
