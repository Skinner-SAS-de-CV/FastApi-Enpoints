"""cambiar_client_id_a_job_id_en_analisis

Revision ID: a1b2c3d4e5f7
Revises: c1a2b3d4e5f6
Create Date: 2026-01-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'c1a2b3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregar columna job_id (nullable temporalmente para migrar datos)
    op.add_column('analisis', sa.Column('job_id', sa.Integer(), nullable=True))

    # Migrar datos existentes: asignar job_id basado en client_id
    op.execute("""
        UPDATE analisis a
        SET job_id = (
            SELECT id FROM tipos_de_trabajo
            WHERE client_id = a.client_id
            LIMIT 1
        )
    """)

    # Crear foreign key para job_id
    op.create_foreign_key(
        'fk_analisis_job_id',
        'analisis',
        'tipos_de_trabajo',
        ['job_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Eliminar foreign key de client_id
    op.drop_constraint('analisis_client_id_fkey', 'analisis', type_='foreignkey')

    # Eliminar columna client_id
    op.drop_column('analisis', 'client_id')

    # Hacer job_id NOT NULL (después de migrar datos)
    op.alter_column('analisis', 'job_id', nullable=False)


def downgrade() -> None:
    # Agregar columna client_id
    op.add_column('analisis', sa.Column('client_id', sa.Integer(), nullable=True))

    # Crear foreign key para client_id
    op.create_foreign_key(
        'analisis_client_id_fkey',
        'analisis',
        'clientes',
        ['client_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Eliminar foreign key de job_id
    op.drop_constraint('fk_analisis_job_id', 'analisis', type_='foreignkey')

    # Eliminar columna job_id
    op.drop_column('analisis', 'job_id')

    # Hacer client_id NOT NULL
    op.alter_column('analisis', 'client_id', nullable=False)
