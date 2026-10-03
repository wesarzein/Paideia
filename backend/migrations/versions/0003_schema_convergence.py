"""converge legacy schemas with current SQLAlchemy metadata

Revision ID: 0003_schema_convergence
Revises: 0002_grade_evaluation_fields
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_schema_convergence"
down_revision: str | None = "0002_grade_evaluation_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS enrollments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id UUID NOT NULL REFERENCES students(id),
            course_id UUID NOT NULL REFERENCES courses(id),
            period_id UUID NOT NULL REFERENCES academic_periods(id),
            status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS follow_ups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id UUID NOT NULL REFERENCES students(id),
            status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
            action VARCHAR(500) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS grade_id UUID")
    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS section_id UUID")
    op.execute(
        "ALTER TABLE grade_records ADD COLUMN IF NOT EXISTS evaluation_name "
        "VARCHAR(120) NOT NULL DEFAULT 'Evaluación'"
    )
    op.execute(
        "ALTER TABLE grade_records ADD COLUMN IF NOT EXISTS evaluation_type "
        "VARCHAR(50) NOT NULL DEFAULT 'Tarea'"
    )
    op.execute(
        "ALTER TABLE grade_records ADD COLUMN IF NOT EXISTS assessment_date DATE "
        "NOT NULL DEFAULT CURRENT_DATE"
    )
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'students'::regclass AND contype = 'f' AND confrelid = 'grades'::regclass
            ) THEN
                ALTER TABLE students ADD CONSTRAINT fk_students_grade_id_grades
                    FOREIGN KEY (grade_id) REFERENCES grades(id);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'students'::regclass AND contype = 'f' AND confrelid = 'sections'::regclass
            ) THEN
                ALTER TABLE students ADD CONSTRAINT fk_students_section_id_sections
                    FOREIGN KEY (section_id) REFERENCES sections(id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE students DROP CONSTRAINT IF EXISTS fk_students_section_id_sections")
    op.execute("ALTER TABLE students DROP CONSTRAINT IF EXISTS fk_students_grade_id_grades")
    op.execute("ALTER TABLE grade_records DROP COLUMN IF EXISTS assessment_date")
    op.execute("ALTER TABLE grade_records DROP COLUMN IF EXISTS evaluation_type")
    op.execute("ALTER TABLE grade_records DROP COLUMN IF EXISTS evaluation_name")
    op.execute("ALTER TABLE students DROP COLUMN IF EXISTS section_id")
    op.execute("ALTER TABLE students DROP COLUMN IF EXISTS grade_id")