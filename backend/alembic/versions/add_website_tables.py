"""Add website tables

Revision ID: 1234567890ab
Revises: 
Create Date: 2025-06-27 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
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
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.Column('embedding', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('chunk_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),  # Changed from 'metadata' to 'chunk_metadata'
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['website_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_website_chunks_document_id'), 'website_chunks', ['document_id'], unique=False)
    
    # Add index on chunk_index for faster lookups
    op.create_index(op.f('ix_website_chunks_chunk_index'), 'website_chunks', ['chunk_index'], unique=False)
    
    # Add index on embedding for vector search (if using PostgreSQL with pgvector)
    # op.execute('CREATE INDEX idx_website_chunks_embedding ON website_chunks USING ivfflat (embedding vector_cosine_ops)')

def downgrade():
    # Drop indexes first
    op.drop_index(op.f('ix_website_chunks_chunk_index'), table_name='website_chunks')
    op.drop_index(op.f('ix_website_chunks_document_id'), table_name='website_chunks')
    op.drop_index(op.f('ix_website_documents_domain'), table_name='website_documents')
    
    # Drop tables
    op.drop_table('website_chunks')
    op.drop_table('website_documents')
    
    # Drop the vector index if it exists
    # op.execute('DROP INDEX IF EXISTS idx_website_chunks_embedding')
