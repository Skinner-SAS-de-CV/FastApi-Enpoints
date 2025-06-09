"""limpiar data de prueba

Revision ID: b036e9be4e52
Revises: 55d7c6a26665
Create Date: 2025-06-09 16:19:53.533045

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b036e9be4e52'
down_revision: Union[str, None] = '55d7c6a26665'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM perfil_del_trabajador"))
    conn.execute(sa.text("DELETE FROM habilidades"))
    conn.execute(sa.text("DELETE FROM funciones_del_trabajo"))
    conn.execute(sa.text("DELETE FROM tipos_de_trabajo"))
    conn.execute(sa.text("DELETE FROM clientes"))
    conn.execute(sa.text("DELETE FROM analisis"))

def downgrade() -> None:
    pass
