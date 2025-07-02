"""merge website tables migration

Revision ID: 5e75f2138d8c
Revises: 536b81c2b491, manual_add_website_tables
Create Date: 2025-06-26 09:46:16.892851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e75f2138d8c'
down_revision: Union[str, None] = '536b81c2b491'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
