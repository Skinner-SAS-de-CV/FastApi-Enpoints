"""migracion_inicial_corregida_y_tabla_usuario

Revision ID: df8de30473d4
Revises: b4bfbbbb0a4c
Create Date: 2025-08-29 05:36:49.453846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'df8de30473d4'
down_revision: Union[str, None] = 'b4bfbbbb0a4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Crear la tabla 'usuario'
    op.create_table(
        'usuario',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('firstname', sa.String(), nullable=False),
        sa.Column('lastname', sa.String(), nullable=False),
        sa.Column('external_user_id', sa.String(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clientes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_user_id')
    )
    op.create_index(op.f('ix_usuario_firstname'), 'usuario', ['firstname'], unique=False)
    op.create_index(op.f('ix_usuario_id'), 'usuario', ['id'], unique=False)
    op.create_index(op.f('ix_usuario_lastname'), 'usuario', ['lastname'], unique=False)

    # 2) Backfill de NULLs en clientes.user_id antes de forzar NOT NULL
    op.execute("UPDATE clientes SET user_id = 'legacy-' || id::text WHERE user_id IS NULL")

    # 3) Ahora sí, hacer NOT NULL
    op.alter_column('clientes', 'user_id', existing_type=sa.VARCHAR(), nullable=False)

    # 4) Eliminar el unique compuesto redundante (name, user_id)
    #    Mantenemos name como único (no tocamos el índice único 'ix_clientes_name')
    op.drop_constraint('name_user_id_unique', 'clientes', type_='unique')


def downgrade() -> None:
    # Revertir: eliminar índices y tabla 'usuario'
    op.drop_index(op.f('ix_usuario_lastname'), table_name='usuario')
    op.drop_index(op.f('ix_usuario_id'), table_name='usuario')
    op.drop_index(op.f('ix_usuario_firstname'), table_name='usuario')
    op.drop_table('usuario')

    # Dejar clientes.user_id nuevamente nullable
    op.alter_column('clientes', 'user_id', existing_type=sa.VARCHAR(), nullable=True)

    # Restaurar el unique compuesto (name, user_id)
    op.create_unique_constraint('name_user_id_unique', 'clientes', ['name', 'user_id'])
    # ### end Alembic commands ###
