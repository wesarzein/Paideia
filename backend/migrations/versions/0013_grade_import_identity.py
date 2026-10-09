"""Reserve grade identities atomically, preserving ambiguous historical groups."""

import sqlalchemy as sa
from alembic import op

revision = "0013_grade_import_identity"
down_revision = "0012_grade_assessment_snapshot"
branch_labels = None
depends_on = None


def upgrade():
    # Hold writers until backfill and trigger are committed together: otherwise
    # an insert between the scan and CREATE TRIGGER could escape reservation.
    op.execute("LOCK TABLE grade_records IN SHARE ROW EXCLUSIVE MODE")
    op.create_table(
        "grade_record_identities",
        sa.Column("identity_key", sa.Text(), primary_key=True),
        sa.Column("grade_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["grade_id"],
            ["grade_records.id"],
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_index("ix_grade_record_identities_grade_id", "grade_record_identities", ["grade_id"])
    op.execute("""
        CREATE FUNCTION academic_grade_identity(
            student uuid, course uuid, period uuid, component uuid,
            evaluation text, evidence text, assessed date
        ) RETURNS text LANGUAGE sql IMMUTABLE AS $$
            SELECT jsonb_build_array(student, course, period, component,
                btrim(evaluation), btrim(evidence), to_char(assessed, 'YYYY-MM-DD'))::text
        $$;
        INSERT INTO grade_record_identities(identity_key, grade_id)
        SELECT academic_grade_identity(student_id, course_id, period_id, component_id,
                   evaluation_name, evaluation_type, assessment_date),
               CASE WHEN count(*) = 1 THEN (array_agg(id ORDER BY id))[1] ELSE NULL END
        FROM grade_records
        GROUP BY academic_grade_identity(student_id, course_id, period_id, component_id,
                   evaluation_name, evaluation_type, assessment_date);

        CREATE FUNCTION reserve_grade_identity() RETURNS trigger LANGUAGE plpgsql AS $$
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
        CREATE TRIGGER grade_identity_guard BEFORE INSERT OR UPDATE ON grade_records
        FOR EACH ROW EXECUTE FUNCTION reserve_grade_identity();
    """)


def downgrade():
    raise RuntimeError("Removing identity reservations would disable grade duplicate protection")
