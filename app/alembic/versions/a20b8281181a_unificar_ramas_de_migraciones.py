"""Unificar ramas de migraciones

Revision ID: a20b8281181a
Revises: 2eacad8ecbae, da5ea9eaeadb
Create Date: 2025-04-30 23:00:28.855953

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a20b8281181a'
down_revision: Union[str, None] = ('2eacad8ecbae', 'da5ea9eaeadb')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
