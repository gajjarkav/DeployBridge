"""increase_render_api_key_length

Revision ID: 7f09806a3b0b
Revises: dad6b157e666
Create Date: 2026-09-17 00:38:15.578458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f09806a3b0b'
down_revision: Union[str, Sequence[str], None] = 'dad6b157e666'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('users', 'render_api_key',
               existing_type=sa.String(length=64),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('users', 'render_owner_id',
               existing_type=sa.String(length=64),
               type_=sa.String(),
               existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'render_api_key',
               existing_type=sa.String(),
               type_=sa.String(length=64),
               existing_nullable=True)
    op.alter_column('users', 'render_owner_id',
               existing_type=sa.String(),
               type_=sa.String(length=64),
               existing_nullable=True)
