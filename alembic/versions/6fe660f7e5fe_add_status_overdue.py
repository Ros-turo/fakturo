"""add status overdue

Revision ID: 6fe660f7e5fe
Revises: 857ac5a0e638
Create Date: 2026-06-11 21:50:19.774194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6fe660f7e5fe'
down_revision: Union[str, Sequence[str], None] = '857ac5a0e638'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE status ADD VALUE 'overdue'")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
