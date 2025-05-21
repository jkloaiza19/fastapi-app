"""Add is_read column to the notifications table

Revision ID: f6b5f8af8f53
Revises: 7c565fffcbff
Create Date: 2025-05-17 22:54:08.300087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6b5f8af8f53'
down_revision: Union[str, None] = '7c565fffcbff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
