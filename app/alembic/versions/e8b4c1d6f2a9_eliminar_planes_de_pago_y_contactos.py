"""eliminar planes de pago y columnas de contacto de clientes

Revision ID: e8b4c1d6f2a9
Revises: 47d7347c4724
Create Date: 2026-05-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e8b4c1d6f2a9'
down_revision: Union[str, None] = '47d7347c4724'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Eliminar tablas de planes de pago (orden por dependencias de FK).
    # Postgres elimina los índices asociados junto con cada tabla.
    op.drop_table('topups_analisis')
    op.drop_table('suscripciones')
    op.drop_table('planes')

    # Eliminar columnas de contacto de clientes.
    op.drop_column('clientes', 'contact_phone')
    op.drop_column('clientes', 'contact_email')

    # Eliminar los tipos ENUM de PostgreSQL que quedaron huérfanos.
    sa.Enum(name='subscriptionstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='planslug').drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # Recrear los tipos ENUM.
    planslug = postgresql.ENUM(
        'FREE', 'MONTHLY', 'QUARTERLY', 'BIANNUAL', 'PREMIUM', 'FULL_ACCESS',
        name='planslug', create_type=False,
    )
    subscriptionstatus = postgresql.ENUM(
        'PENDING', 'ACTIVE', 'EXPIRED', 'CANCELLED',
        name='subscriptionstatus', create_type=False,
    )
    planslug.create(op.get_bind(), checkfirst=True)
    subscriptionstatus.create(op.get_bind(), checkfirst=True)

    # Recrear columnas de contacto.
    op.add_column('clientes', sa.Column('contact_email', sa.String(), nullable=True))
    op.add_column('clientes', sa.Column('contact_phone', sa.String(), nullable=True))

    # Recrear tablas de planes de pago.
    op.create_table(
        'planes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('slug', planslug, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('price_usd', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('analyses_limit', sa.Integer(), nullable=True),
        sa.Column('reports_limit', sa.Integer(), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    op.create_table(
        'suscripciones',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('status', subscriptionstatus, nullable=False),
        sa.Column('analyses_used', sa.Integer(), nullable=False),
        sa.Column('reports_used', sa.Integer(), nullable=False),
        sa.Column('starts_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('activated_by', sa.Integer(), nullable=True),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['activated_by'], ['usuario.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['client_id'], ['clientes.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['plan_id'], ['planes.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_suscripciones_client_id', 'suscripciones', ['client_id'], unique=False)
    op.create_index('ix_suscripciones_expires_at', 'suscripciones', ['expires_at'], unique=False)
    op.create_index('ix_suscripciones_status', 'suscripciones', ['status'], unique=False)
    op.create_table(
        'topups_analisis',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('analysis_added', sa.Integer(), nullable=False),
        sa.Column('price_usd', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', subscriptionstatus, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['subscription_id'], ['suscripciones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
