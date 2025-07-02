"""add_website_tables

Revision ID: 4cf3bb6cc367
Revises: a55c413ac837
Create Date: 2025-06-27 12:11:16.008056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cf3bb6cc367'
down_revision: Union[str, None] = 'a55c413ac837'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create website_documents table
    op.create_table(
        'website_documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('domain', sa.String(), nullable=True, index=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('document_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_id'),
        sa.UniqueConstraint('url')
    )
    op.create_index(op.f('ix_website_documents_domain'), 'website_documents', ['domain'], unique=False)
    
    # Create website_chunks table
    op.create_table(
        'website_chunks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.JSON(), nullable=False),
        sa.Column('chunk_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['website_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_website_chunks_document_id'), 'website_chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_website_chunks_chunk_index'), 'website_chunks', ['chunk_index'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index(op.f('ix_website_chunks_chunk_index'), table_name='website_chunks')
    op.drop_index(op.f('ix_website_chunks_document_id'), table_name='website_chunks')
    op.drop_index(op.f('ix_website_documents_domain'), table_name='website_documents')
    
    # Drop tables
    op.drop_table('website_chunks')
    op.drop_table('website_documents')
