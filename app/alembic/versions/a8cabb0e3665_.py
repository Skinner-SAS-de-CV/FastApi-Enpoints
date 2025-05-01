"""empty message

Revision ID: a8cabb0e3665
Revises: 2eacad8ecbae, c024499cd841
Create Date: 2025-05-01 02:18:23.883330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8cabb0e3665'
down_revision: Union[str, None] = ('2eacad8ecbae', 'c024499cd841')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
