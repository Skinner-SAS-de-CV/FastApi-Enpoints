"""anadiendo columnas nuevas a la base de datos

Revision ID: b4bfbbbb0a4c
Revises: 33941fb94a04
Create Date: 2025-08-27 04:40:33.284802

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4bfbbbb0a4c'
down_revision: Union[str, None] = '33941fb94a04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Agregar user_id a clientes
    op.add_column('clientes', sa.Column('user_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_clientes_user_id'), 'clientes', ['user_id'], unique=False)
    
    # Agregar constraint único compuesto
    op.create_unique_constraint('name_user_id_unique', 'clientes', ['name', 'user_id'])
    
    # Agregar campos de timestamp a tipos_de_trabajo
    op.add_column('tipos_de_trabajo', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('tipos_de_trabajo', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Establecer valores por defecto para los campos de timestamp
    op.execute("UPDATE tipos_de_trabajo SET created_at = NOW() WHERE created_at IS NULL")
    op.execute("UPDATE tipos_de_trabajo SET updated_at = NOW() WHERE updated_at IS NULL")
    
    # Hacer los campos not null después de llenarlos
    op.alter_column('tipos_de_trabajo', 'created_at', nullable=False)
    op.alter_column('tipos_de_trabajo', 'updated_at', nullable=False)

def downgrade():
    op.drop_constraint('name_user_id_unique', 'clientes', type_='unique')
    op.drop_index(op.f('ix_clientes_user_id'), table_name='clientes')
    op.drop_column('clientes', 'user_id')
    op.drop_column('tipos_de_trabajo', 'updated_at')
    op.drop_column('tipos_de_trabajo', 'created_at')
    # ### end Alembic commands ###
