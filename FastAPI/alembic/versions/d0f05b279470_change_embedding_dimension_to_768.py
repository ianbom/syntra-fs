"""change_embedding_dimension_to_768

Revision ID: d0f05b279470
Revises: ef01c0815d41
Create Date: 2026-01-17 04:33:05.900628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = 'd0f05b279470'
down_revision: Union[str, None] = 'ef01c0815d41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change embedding column from 1536 to 768 dimensions
    op.alter_column('document_chunks', 'embedding',
               existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=1536),
               type_=pgvector.sqlalchemy.vector.VECTOR(dim=768),
               existing_nullable=True)


def downgrade() -> None:
    # Revert to 1536 dimensions
    op.alter_column('document_chunks', 'embedding',
               existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=768),
               type_=pgvector.sqlalchemy.vector.VECTOR(dim=1536),
               existing_nullable=True)
