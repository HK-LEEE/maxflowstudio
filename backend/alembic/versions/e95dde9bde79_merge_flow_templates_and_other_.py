"""Merge flow templates and other migrations

Revision ID: e95dde9bde79
Revises: 6f7cb4de1879, create_flow_templates_table
Create Date: 2025-07-04 08:00:53.754383

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e95dde9bde79'
down_revision: Union[str, Sequence[str], None] = ('6f7cb4de1879', 'create_flow_templates_table')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
