"""rename_metadata_column

Revision ID: a55c413ac837
Revises: 37f3e608d90f
Create Date: 2025-06-26 10:27:28.766063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a55c413ac837'
down_revision: Union[str, None] = '37f3e608d90f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('files', sa.Column('file_metadata', sa.JSON(), nullable=True))
    op.add_column('files', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('files', sa.Column('page_count', sa.Integer(), nullable=True))
    op.add_column('files', sa.Column('chunk_count', sa.Integer(), nullable=True))
    op.add_column('files', sa.Column('is_processed', sa.Boolean(), nullable=True, default=False))
    op.add_column('files', sa.Column('processing_error', sa.Text(), nullable=True))
    op.add_column('pdf_documents', sa.Column('document_metadata', sa.JSON(), nullable=True))
    op.add_column('csv_documents', sa.Column('header', sa.JSON(), nullable=True))
    op.add_column('xlsx_documents', sa.Column('sheet_names', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('files', 'file_metadata')
    op.drop_column('files', 'file_size')
    op.drop_column('files', 'page_count')
    op.drop_column('files', 'chunk_count')
    op.drop_column('files', 'is_processed')
    op.drop_column('files', 'processing_error')
    op.drop_column('pdf_documents', 'document_metadata')
    op.drop_column('csv_documents', 'header')
    op.drop_column('xlsx_documents', 'sheet_names')
