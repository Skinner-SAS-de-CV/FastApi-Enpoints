"""eliminar_indice_feedback_analisis

Revision ID: c1a2b3d4e5f6
Revises: b957f08eea0d
Create Date: 2026-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, None] = 'b957f08eea0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Eliminar el índice que causa el error con textos largos
    op.drop_index('ix_analisis_feedback', table_name='analisis')


def downgrade() -> None:
    # Recrear el índice si se hace rollback
    op.create_index('ix_analisis_feedback', 'analisis', ['feedback'], unique=False)
