"""normalize grade evidence values to institutional rubric

Revision ID: 0011_evidence_types
Revises: 0010_family_account_links
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_evidence_types"
down_revision: str | None = "0010_family_account_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE grade_records
            SET evaluation_type = CASE
                WHEN lower(trim(evaluation_type)) IN ('actitud', 'actitud ante el area', 'actitud ante el área')
                    THEN 'Actitud ante el área'
                WHEN lower(trim(evaluation_type)) = 'cuaderno' THEN 'Cuaderno'
                WHEN lower(trim(evaluation_type)) IN ('modulo', 'módulo', 'practica', 'práctica')
                    THEN 'Módulo'
                WHEN lower(trim(evaluation_type)) IN (
                    'exposicion', 'exposición', 'exposicion/trabajos', 'exposición/trabajos',
                    'exposicion-trabajos', 'exposición-trabajos', 'trabajo', 'trabajos', 'tarea'
                ) THEN 'Exposición-Trabajos'
                ELSE 'Evaluación'
            END
            """
        )
    )
    op.alter_column(
        "grade_records",
        "evaluation_type",
        existing_type=sa.String(length=50),
        server_default="Actitud ante el área",
    )


def downgrade() -> None:
    op.alter_column(
        "grade_records",
        "evaluation_type",
        existing_type=sa.String(length=50),
        server_default="Tarea",
    )
