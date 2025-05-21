"""Add notifications table

Revision ID: 7c565fffcbff
Revises: f80feff8965a
Create Date: 2025-05-17 22:27:16.278340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c565fffcbff'
down_revision: Union[str, None] = 'f80feff8965a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
