"""add project category

Revision ID: d4a8f1c2e7b9
Revises: c7e1a9d3f2b8
Create Date: 2026-10-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4a8f1c2e7b9'
down_revision: Union[str, None] = 'c7e1a9d3f2b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('category', sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'category')
