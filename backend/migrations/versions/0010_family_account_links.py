"""link student and parent accounts to students

Revision ID: 0010_family_account_links
Revises: 0009_roster_catalog
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_family_account_links"
down_revision: str | None = "0009_roster_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column(
            "student_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_unique_constraint(
        "uq_students_student_user_id", "students", ["student_user_id"]
    )
    op.add_column(
        "students",
        sa.Column(
            "parent_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_students_parent_user_id", "students", ["parent_user_id"])


def downgrade() -> None:
    op.drop_index("ix_students_parent_user_id", table_name="students")
    op.drop_column("students", "parent_user_id")
    op.drop_constraint("uq_students_student_user_id", "students", type_="unique")
    op.drop_column("students", "student_user_id")
