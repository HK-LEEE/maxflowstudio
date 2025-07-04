"""Add workspace and permission models

Revision ID: 002
Revises: 001
Create Date: 2024-06-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '4288b7e284a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add group_id to users table
    op.add_column('users', sa.Column('group_id', sa.String(length=100), nullable=True))
    
    # Create workspaces table
    op.create_table('workspaces',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.Enum('USER', 'GROUP', name='workspacetype'), nullable=False),
        sa.Column('creator_user_id', sa.String(length=36), nullable=False),
        sa.Column('group_id', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['creator_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create workspace_permissions table
    op.create_table('workspace_permissions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('group_id', sa.String(length=100), nullable=True),
        sa.Column('permission_type', sa.Enum('OWNER', 'ADMIN', 'MEMBER', 'VIEWER', name='permissiontype'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'user_id', name='unique_workspace_user_permission'),
        sa.UniqueConstraint('workspace_id', 'group_id', name='unique_workspace_group_permission')
    )
    
    # Create flow_studio_workspace_map table
    op.create_table('flow_studio_workspace_map',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('flow_id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flow_id', name='unique_flow_workspace')
    )
    
    # Create unique index on flow_id for flow_studio_workspace_map
    op.create_index('ix_flow_studio_workspace_map_flow_id', 'flow_studio_workspace_map', ['flow_id'], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_flow_studio_workspace_map_flow_id', table_name='flow_studio_workspace_map')
    op.drop_table('flow_studio_workspace_map')
    op.drop_table('workspace_permissions')
    op.drop_table('workspaces')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS workspacetype')
    op.execute('DROP TYPE IF EXISTS permissiontype')
    
    # Remove group_id from users table
    op.drop_column('users', 'group_id')