"""add_documents_and_chunks_tables

Revision ID: ef01c0815d41
Revises: c05c3fb71d9f
Create Date: 2026-01-17 04:19:30.134039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision: str = 'ef01c0815d41'
down_revision: Union[str, None] = 'c05c3fb71d9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create documents table
    op.create_table('documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('creator', sa.Text(), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('publisher', sa.Text(), nullable=True),
        sa.Column('contributor', sa.Text(), nullable=True),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('type', sa.Enum('JOURNAL', 'CONFERENCE', 'THESIS', 'REPORT', 'BOOK', name='documenttype'), nullable=True),
        sa.Column('format', sa.Text(), nullable=True),
        sa.Column('identifier', sa.Text(), nullable=True),
        sa.Column('source', sa.Text(), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('relation', sa.Text(), nullable=True),
        sa.Column('coverage', sa.Text(), nullable=True),
        sa.Column('rights', sa.Text(), nullable=True),
        sa.Column('doi', sa.String(length=150), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('citation_count', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('is_private', sa.Boolean(), nullable=True),
        sa.Column('is_metadata_complete', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_doi'), 'documents', ['doi'], unique=True)
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)
    op.create_index(op.f('ix_documents_title'), 'documents', ['title'], unique=False)
    
    # Create document_chunks table
    op.create_table('document_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=True),
        sa.Column('chunk_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('section_title', sa.Text(), nullable=True),
        sa.Column('chunk_type', sa.Enum('TITLE', 'ABSTRACT', 'PARAGRAPH', 'TABLE', 'REFERENCE', name='chunktype'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_id'), 'document_chunks', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_document_chunks_id'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_document_id'), table_name='document_chunks')
    op.drop_table('document_chunks')
    op.drop_index(op.f('ix_documents_title'), table_name='documents')
    op.drop_index(op.f('ix_documents_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_doi'), table_name='documents')
    op.drop_table('documents')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS chunktype')
    op.execute('DROP TYPE IF EXISTS documenttype')
