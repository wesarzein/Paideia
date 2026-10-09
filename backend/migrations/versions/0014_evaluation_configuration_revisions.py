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
    op.add_column("grade_records", sa.Column("academic_bimester", sa.Integer(), nullable=True))
    op.add_column("grade_records", sa.Column("evaluation_block", sa.Integer(), nullable=True))
    op.add_column(
        "grade_records", sa.Column("evaluation_criterion_key", sa.String(length=64), nullable=True)
    )
    op.create_check_constraint(
        "ck_grade_records_positive_bimester",
        "grade_records",
        "academic_bimester IS NULL OR academic_bimester > 0",
    )
    op.create_check_constraint(
        "ck_grade_records_evaluation_block",
        "grade_records",
        "evaluation_block IS NULL OR evaluation_block IN (1, 2)",
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
    op.create_index(
        "ix_grade_records_evaluation_criterion_key",
        "grade_records",
        ["evaluation_criterion_key"],
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

        CREATE FUNCTION academic_grade_identity_v2(
            student uuid, course uuid, period uuid, component uuid,
            evaluation text, evidence text, assessed date, criterion text
        ) RETURNS text LANGUAGE sql IMMUTABLE AS $$
            SELECT CASE WHEN criterion IS NULL THEN
                academic_grade_identity(student, course, period, component,
                    evaluation, evidence, assessed)
            ELSE jsonb_build_array(student, course, period, component,
                btrim(evaluation), btrim(evidence), to_char(assessed, 'YYYY-MM-DD'),
                btrim(criterion))::text END
        $$;

        CREATE OR REPLACE FUNCTION reserve_grade_identity() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE new_key text; old_key text;
        BEGIN
            new_key := academic_grade_identity_v2(NEW.student_id, NEW.course_id, NEW.period_id,
                NEW.component_id, NEW.evaluation_name, NEW.evaluation_type, NEW.assessment_date,
                NEW.evaluation_criterion_key);
            IF TG_OP = 'UPDATE' THEN
                old_key := academic_grade_identity_v2(OLD.student_id, OLD.course_id, OLD.period_id,
                    OLD.component_id, OLD.evaluation_name, OLD.evaluation_type,
                    OLD.assessment_date, OLD.evaluation_criterion_key);
                IF new_key = old_key THEN RETURN NEW; END IF;
            END IF;
            INSERT INTO grade_record_identities(identity_key, grade_id) VALUES (new_key, NEW.id);
            IF TG_OP = 'UPDATE' THEN
                DELETE FROM grade_record_identities
                WHERE identity_key = old_key AND grade_id = OLD.id;
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE OR REPLACE FUNCTION preserve_grade_assessment_config() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE c record; r record; criterion jsonb;
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF NEW.assessment_weight IS DISTINCT FROM OLD.assessment_weight
                   OR NEW.assessment_config::jsonb IS DISTINCT FROM OLD.assessment_config::jsonb
                   OR NEW.evaluation_revision_id IS DISTINCT FROM OLD.evaluation_revision_id
                   OR NEW.academic_bimester IS DISTINCT FROM OLD.academic_bimester
                   OR NEW.evaluation_block IS DISTINCT FROM OLD.evaluation_block
                   OR NEW.evaluation_criterion_key IS DISTINCT FROM OLD.evaluation_criterion_key
                THEN
                    RAISE EXCEPTION 'Historical grade assessment configuration is immutable';
                END IF;
                RETURN NEW;
            END IF;
            SELECT weight, name, is_optional INTO c
            FROM course_assessment_components WHERE id = NEW.component_id FOR SHARE;
            IF NEW.evaluation_revision_id IS NOT NULL THEN
                SELECT id, course_id, period_id, version, state, content_hash, configuration INTO r
                FROM evaluation_configuration_revisions
                WHERE id = NEW.evaluation_revision_id FOR SHARE;
                IF NOT FOUND OR r.state <> 'published'
                   OR r.course_id <> NEW.course_id OR r.period_id <> NEW.period_id
                THEN
                    RAISE EXCEPTION 'Invalid published evaluation revision for grade';
                END IF;
                IF NEW.academic_bimester IS NULL OR NEW.academic_bimester < 1
                   OR NEW.evaluation_block NOT IN (1, 2)
                   OR NEW.evaluation_criterion_key IS NULL
                THEN
                    RAISE EXCEPTION 'Configurable grade requires bimester, block and criterion';
                END IF;
                SELECT item INTO criterion
                FROM jsonb_array_elements(r.configuration::jsonb->'criteria') item
                WHERE item->>'key' = NEW.evaluation_criterion_key;
                IF criterion IS NULL OR (criterion->>'is_active')::boolean IS NOT TRUE
                   OR (criterion->>'block')::integer <> NEW.evaluation_block
                THEN
                    RAISE EXCEPTION 'Criterion is not active in the published block';
                END IF;
            END IF;
            NEW.assessment_weight := CASE WHEN criterion IS NULL THEN coalesce(c.weight, 1.0)
                ELSE (criterion->>'weight')::double precision END;
            NEW.assessment_config := json_build_object(
                'schema_version', CASE WHEN r.id IS NULL THEN 1 ELSE 2 END,
                'algorithm', 'weighted_mean_v1',
                'origin', 'record_insert', 'component_id', NEW.component_id,
                'component_name', coalesce(criterion->>'name', c.name),
                'is_optional', coalesce((criterion->>'is_optional')::boolean, c.is_optional),
                'weight', NEW.assessment_weight,
                'academic_bimester', NEW.academic_bimester,
                'evaluation_block', NEW.evaluation_block,
                'evaluation_criterion_key', NEW.evaluation_criterion_key,
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
        CREATE OR REPLACE FUNCTION reserve_grade_identity() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE new_key text; old_key text;
        BEGIN
            new_key := academic_grade_identity(NEW.student_id, NEW.course_id, NEW.period_id,
                NEW.component_id, NEW.evaluation_name, NEW.evaluation_type, NEW.assessment_date);
            IF TG_OP = 'UPDATE' THEN
                old_key := academic_grade_identity(OLD.student_id, OLD.course_id, OLD.period_id,
                    OLD.component_id, OLD.evaluation_name, OLD.evaluation_type,
                    OLD.assessment_date);
                IF new_key = old_key THEN RETURN NEW; END IF;
            END IF;
            INSERT INTO grade_record_identities(identity_key, grade_id) VALUES (new_key, NEW.id);
            IF TG_OP = 'UPDATE' THEN
                DELETE FROM grade_record_identities
                WHERE identity_key = old_key AND grade_id = OLD.id;
            END IF;
            RETURN NEW;
        END;
        $$;
        DROP FUNCTION academic_grade_identity_v2(uuid, uuid, uuid, uuid, text, text, date, text);

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
    op.drop_index("ix_grade_records_evaluation_criterion_key", table_name="grade_records")
    op.drop_constraint(
        "fk_grade_records_evaluation_revision", "grade_records", type_="foreignkey"
    )
    op.drop_column("grade_records", "evaluation_revision_id")
    op.drop_constraint(
        "ck_grade_records_evaluation_block", "grade_records", type_="check"
    )
    op.drop_constraint(
        "ck_grade_records_positive_bimester", "grade_records", type_="check"
    )
    op.drop_column("grade_records", "evaluation_criterion_key")
    op.drop_column("grade_records", "evaluation_block")
    op.drop_column("grade_records", "academic_bimester")
    op.drop_index("ix_evaluation_revision_scope", table_name="evaluation_configuration_revisions")
    op.drop_table("evaluation_configuration_revisions")
