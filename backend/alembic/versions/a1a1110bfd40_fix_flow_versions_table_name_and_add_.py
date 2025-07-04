"""Fix flow_versions table name and add api_deployments

Revision ID: a1a1110bfd40
Revises: 002
Create Date: 2025-06-24 18:32:51.844480

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1a1110bfd40'
down_revision: Union[str, Sequence[str], None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # This migration was created to document the existing database state
    # The database was already created with the correct schema via setup_database.py
    # No actual changes needed as tables already exist with correct structure
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # No downgrade needed as this was a no-op migration
    pass
