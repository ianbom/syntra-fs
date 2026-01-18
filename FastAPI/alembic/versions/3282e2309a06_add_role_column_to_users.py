"""add_role_column_to_users

Revision ID: 3282e2309a06
Revises: d0f05b279470
Create Date: 2026-01-19 00:16:43.064498

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3282e2309a06'
down_revision: Union[str, None] = 'd0f05b279470'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type first
    userrole_enum = sa.Enum('admin', 'user', name='userrole')
    userrole_enum.create(op.get_bind(), checkfirst=True)
    
    # Add column with server_default for existing rows
    op.add_column('users', sa.Column('role', userrole_enum, nullable=False, server_default='user'))


def downgrade() -> None:
    op.drop_column('users', 'role')
    # Drop the enum type
    sa.Enum(name='userrole').drop(op.get_bind(), checkfirst=True)
