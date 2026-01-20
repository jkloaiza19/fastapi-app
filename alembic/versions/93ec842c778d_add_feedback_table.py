"""Add Feedback table

Revision ID: 93ec842c778d
Revises: f6b5f8af8f53
Create Date: 2026-01-09 22:54:35.575310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93ec842c778d'
down_revision: Union[str, None] = 'f6b5f8af8f53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
