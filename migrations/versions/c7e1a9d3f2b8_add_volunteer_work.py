"""add volunteer work

Revision ID: c7e1a9d3f2b8
Revises: b2c04cf6e9d4
Create Date: 2026-10-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c7e1a9d3f2b8'
down_revision: Union[str, None] = 'b2c04cf6e9d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('volunteer_work',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=160), nullable=False),
    sa.Column('organization', sa.String(length=160), nullable=True),
    sa.Column('start_date', sa.String(length=80), nullable=True),
    sa.Column('end_date', sa.String(length=80), nullable=True),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('volunteer_work')
