"""add versioning and cycle tracking

Revision ID: 0002_add_versioning_and_cycles
Revises: 0001_initial_schema
Create Date: 2026-10-31 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0002_add_versioning_and_cycles'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Resolutions: add version and is_current
    with op.batch_alter_table('resolutions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('is_current', sa.Boolean(), nullable=False, server_default='1'))

    # 2. Surveys: add cycle
    with op.batch_alter_table('surveys', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cycle', sa.Integer(), nullable=False, server_default='1'))

    # 3. SLA Clocks: add cycle and is_current
    with op.batch_alter_table('sla_clocks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cycle', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('is_current', sa.Boolean(), nullable=False, server_default='1'))

def downgrade() -> None:
    with op.batch_alter_table('sla_clocks', schema=None) as batch_op:
        batch_op.drop_column('is_current')
        batch_op.drop_column('cycle')

    with op.batch_alter_table('surveys', schema=None) as batch_op:
        batch_op.drop_column('cycle')

    with op.batch_alter_table('resolutions', schema=None) as batch_op:
        batch_op.drop_column('is_current')
        batch_op.drop_column('version')

