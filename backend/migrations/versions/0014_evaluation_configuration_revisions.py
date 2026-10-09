"""Add immutable, versioned evaluation configurations and bind new grades."""

import sqlalchemy as sa
from alembic import op

revision = "0014_evaluation_configuration_revisions"
down_revision = "0013_grade_import_identity"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "evaluation_configuration_revisions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("period_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("previous_revision_id", sa.UUID(), nullable=True),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("version > 0", name="ck_evaluation_revision_positive_version"),
        sa.CheckConstraint(
            "state IN ('draft', 'published')", name="ck_evaluation_revision_state"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["period_id"], ["academic_periods.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["previous_revision_id"],
            ["evaluation_configuration_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "course_id", "period_id", "version", name="uq_evaluation_revision_scope_version"
        ),
    )
    op.create_index(
        "ix_evaluation_revision_scope",
        "evaluation_configuration_revisions",
        ["course_id", "period_id", "version"],
    )
    op.add_column(
        "grade_records", sa.Column("evaluation_revision_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "fk_grade_records_evaluation_revision",
        "grade_records",
        "evaluation_configuration_revisions",
        ["evaluation_revision_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_grade_records_evaluation_revision_id", "grade_records", ["evaluation_revision_id"]
    )

    op.execute("""
        CREATE FUNCTION reject_evaluation_revision_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Evaluation configuration revisions are append-only';
        END;
        $$;
        CREATE TRIGGER evaluation_revision_append_only
        BEFORE UPDATE OR DELETE ON evaluation_configuration_revisions
        FOR EACH ROW EXECUTE FUNCTION reject_evaluation_revision_change();

        CREATE OR REPLACE FUNCTION preserve_grade_assessment_config() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE c record; r record;
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF NEW.assessment_weight IS DISTINCT FROM OLD.assessment_weight
                   OR NEW.assessment_config::jsonb IS DISTINCT FROM OLD.assessment_config::jsonb
                   OR NEW.evaluation_revision_id IS DISTINCT FROM OLD.evaluation_revision_id
                THEN
                    RAISE EXCEPTION 'Historical grade assessment configuration is immutable';
                END IF;
                RETURN NEW;
            END IF;
            SELECT weight, name, is_optional INTO c
            FROM course_assessment_components WHERE id = NEW.component_id FOR SHARE;
            IF NEW.evaluation_revision_id IS NOT NULL THEN
                SELECT id, course_id, period_id, version, state, content_hash INTO r
                FROM evaluation_configuration_revisions
                WHERE id = NEW.evaluation_revision_id FOR SHARE;
                IF NOT FOUND OR r.state <> 'published'
                   OR r.course_id <> NEW.course_id OR r.period_id <> NEW.period_id
                THEN
                    RAISE EXCEPTION 'Invalid published evaluation revision for grade';
                END IF;
            END IF;
            NEW.assessment_weight := coalesce(c.weight, 1.0);
            NEW.assessment_config := json_build_object(
                'schema_version', 1, 'algorithm', 'weighted_mean_v1',
                'origin', 'record_insert', 'component_id', NEW.component_id,
                'component_name', c.name, 'is_optional', c.is_optional,
                'weight', NEW.assessment_weight,
                'evaluation_revision_id', CASE WHEN r.id IS NULL THEN NULL ELSE r.id::text END,
                'evaluation_revision_version', r.version,
                'evaluation_revision_hash', r.content_hash
            );
            RETURN NEW;
        END;
        $$;
    """)


def downgrade():
    op.execute("""
        CREATE OR REPLACE FUNCTION preserve_grade_assessment_config() RETURNS trigger
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
        DROP TRIGGER evaluation_revision_append_only ON evaluation_configuration_revisions;
        DROP FUNCTION reject_evaluation_revision_change();
    """)
    op.drop_index("ix_grade_records_evaluation_revision_id", table_name="grade_records")
    op.drop_constraint(
        "fk_grade_records_evaluation_revision", "grade_records", type_="foreignkey"
    )
    op.drop_column("grade_records", "evaluation_revision_id")
    op.drop_index("ix_evaluation_revision_scope", table_name="evaluation_configuration_revisions")
    op.drop_table("evaluation_configuration_revisions")
