"""Freeze the calculation basis of recorded grades without changing their values."""

import sqlalchemy as sa
from alembic import op

revision = "0012_grade_assessment_snapshot"
down_revision = "0011_evidence_types"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("grade_records", sa.Column("assessment_weight", sa.Float(), nullable=True))
    op.add_column("grade_records", sa.Column("assessment_config", sa.JSON(), nullable=True))
    # A LEFT JOIN preserves grades without components, including imported records.
    op.execute("""
        UPDATE grade_records g SET
            assessment_weight = s.weight,
            assessment_config = json_build_object(
                'schema_version', 1, 'algorithm', 'weighted_mean_v1',
                'origin', 'legacy_migration', 'component_id', g.component_id,
                'component_name', s.name, 'is_optional', s.is_optional, 'weight', s.weight
            )
        FROM (
            SELECT r.id, coalesce(c.weight, 1.0) AS weight, c.name, c.is_optional
            FROM grade_records r
            LEFT JOIN course_assessment_components c ON c.id = r.component_id
        ) s WHERE s.id = g.id
    """)
    op.alter_column("grade_records", "assessment_weight", nullable=False)
    op.alter_column("grade_records", "assessment_config", nullable=False)
    # DB enforcement also covers bulk/raw SQL writers and prevents snapshot edits.
    op.execute("""
        CREATE FUNCTION preserve_grade_assessment_config() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE c record;
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF NEW.assessment_weight IS DISTINCT FROM OLD.assessment_weight
                   OR NEW.assessment_config::jsonb IS DISTINCT FROM OLD.assessment_config::jsonb
                THEN
                    RAISE EXCEPTION 'Historical grade assessment configuration is immutable';
                END IF;
                RETURN NEW;
            END IF;
            SELECT weight, name, is_optional INTO c
            FROM course_assessment_components WHERE id = NEW.component_id FOR SHARE;
            NEW.assessment_weight := coalesce(c.weight, 1.0);
            NEW.assessment_config := json_build_object(
                'schema_version', 1, 'algorithm', 'weighted_mean_v1',
                'origin', 'record_insert', 'component_id', NEW.component_id,
                'component_name', c.name, 'is_optional', c.is_optional,
                'weight', NEW.assessment_weight
            );
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER grade_assessment_config_guard
        BEFORE INSERT OR UPDATE ON grade_records
        FOR EACH ROW EXECUTE FUNCTION preserve_grade_assessment_config();
    """)


def downgrade():
    # Removing historical evidence is intentionally unsupported.
    raise RuntimeError("Snapshot migration cannot be downgraded without losing historical evidence")
