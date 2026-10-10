"""Preserve academic before/after images independently of working rows."""

import sqlalchemy as sa
from alembic import op

revision = "0017_academic_change_history"
down_revision = "0016_local_risk_models"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "academic_change_history",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity", sa.String(40), nullable=False),
        sa.Column("record_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID()),
        sa.Column("operation", sa.String(10), nullable=False),
        sa.Column("actor_id", sa.UUID()),
        sa.Column("actor_role", sa.String(30)),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("authorization", sa.JSON()),
        sa.Column("before", sa.JSON()),
        sa.Column("after", sa.JSON()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.CheckConstraint(
            "operation IN ('INSERT','UPDATE','DELETE')", name="academic_history_operation"
        ),
        # Deliberately no cascading FK: history survives removal of working rows.
    )
    op.create_index(
        "ix_academic_history_student", "academic_change_history", ["student_id", "created_at"]
    )
    op.execute("""
        CREATE FUNCTION capture_academic_change() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE prior jsonb; following jsonb; item jsonb; actor text;
        BEGIN
            IF TG_OP <> 'INSERT' THEN prior := to_jsonb(OLD); END IF;
            IF TG_OP <> 'DELETE' THEN following := to_jsonb(NEW); END IF;
            IF TG_OP = 'UPDATE' AND prior = following THEN RETURN NEW; END IF;
            item := coalesce(following, prior);
            actor := nullif(current_setting('paideia.actor_id', true), '');
            INSERT INTO academic_change_history
                (entity, record_id, student_id, course_id, operation, actor_id,
                 actor_role, source, "authorization", before, after)
            VALUES (TG_TABLE_NAME, (item->>'id')::uuid, (item->>'student_id')::uuid,
                (item->>'course_id')::uuid, TG_OP, actor::uuid,
                nullif(current_setting('paideia.actor_role', true), ''),
                CASE WHEN actor IS NULL THEN 'database' ELSE 'authenticated_api' END,
                nullif(current_setting('paideia.authorization', true), '')::jsonb,
                prior, following);
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END;
        $$;
        CREATE FUNCTION reject_academic_history_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Academic change history is append-only'; END;
        $$;
        CREATE TRIGGER academic_history_append_only
        BEFORE UPDATE OR DELETE ON academic_change_history
        FOR EACH ROW EXECUTE FUNCTION reject_academic_history_change();
        CREATE TRIGGER academic_history_no_truncate
        BEFORE TRUNCATE ON academic_change_history
        FOR EACH STATEMENT EXECUTE FUNCTION reject_academic_history_change();
    """)
    for table in ("grade_records", "attendance_records", "follow_ups"):
        op.execute(
            "CREATE TRIGGER academic_change_history_capture "
            f"AFTER INSERT OR UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION capture_academic_change()"
        )


def downgrade():
    raise RuntimeError("Removing academic audit history would lose preserved evidence")
