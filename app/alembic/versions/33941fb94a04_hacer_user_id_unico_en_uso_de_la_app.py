"""Hacer user_id unico en uso_de_la_app

Revision ID: 33941fb94a04
Revises: c725894ba888
Create Date: 2025-07-08 02:05:25.961457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33941fb94a04'
down_revision: Union[str, None] = 'c725894ba888'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, 'uso_de_la_app', ['user_id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'uso_de_la_app', type_='unique')
    # ### end Alembic commands ###
