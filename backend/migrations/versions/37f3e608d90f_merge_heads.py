"""merge heads

Revision ID: 37f3e608d90f
Revises: 5e75f2138d8c, 1234567890ab
Create Date: 2025-06-26 10:19:55.555127

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37f3e608d90f'
down_revision: Union[str, None] = '5e75f2138d8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
