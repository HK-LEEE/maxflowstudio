"""create flow_templates table

Revision ID: create_flow_templates_table
Revises: 
Create Date: 2025-01-03 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_flow_templates_table'
down_revision = None  # 이전 마이그레이션 ID로 변경 필요
branch_labels = None
depends_on = None


def upgrade():
    """Create flow_templates table"""
    op.create_table(
        'flow_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('definition', postgresql.JSON(), nullable=False),
        sa.Column('thumbnail', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
    )
    
    # 인덱스 생성
    op.create_index('ix_flow_templates_id', 'flow_templates', ['id'])
    op.create_index('ix_flow_templates_name', 'flow_templates', ['name'])
    op.create_index('ix_flow_templates_category', 'flow_templates', ['category'])
    op.create_index('ix_flow_templates_created_at', 'flow_templates', ['created_at'])
    op.create_index('ix_flow_templates_is_public', 'flow_templates', ['is_public'])


def downgrade():
    """Drop flow_templates table"""
    op.drop_index('ix_flow_templates_is_public', table_name='flow_templates')
    op.drop_index('ix_flow_templates_created_at', table_name='flow_templates')
    op.drop_index('ix_flow_templates_category', table_name='flow_templates')
    op.drop_index('ix_flow_templates_name', table_name='flow_templates')
    op.drop_index('ix_flow_templates_id', table_name='flow_templates')
    op.drop_table('flow_templates')