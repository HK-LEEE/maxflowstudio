"""Add RAG tables for document learning and search

Revision ID: add_rag_tables
Revises: e95dde9bde79
Create Date: 2025-01-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_rag_tables'
down_revision = 'e95dde9bde79'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types using raw SQL to avoid conflicts
    op.execute("CREATE TYPE ragcollectionstatus AS ENUM ('active', 'learning', 'error', 'inactive')")
    op.execute("CREATE TYPE ragdocumentstatus AS ENUM ('pending', 'processing', 'completed', 'error', 'deleted')")
    op.execute("CREATE TYPE ragdocumenttype AS ENUM ('pdf', 'docx', 'txt', 'md', 'html')")
    
    # Create rag_collections table
    op.create_table(
        'rag_collections',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='active'),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('vector_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('qdrant_collection_name', sa.String(length=255), nullable=False),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('updated_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for rag_collections
    op.create_index('ix_rag_collections_workspace_id', 'rag_collections', ['workspace_id'])
    op.create_index('ix_rag_collections_name', 'rag_collections', ['name'])
    op.create_index('ix_rag_collections_qdrant_collection_name', 'rag_collections', ['qdrant_collection_name'])
    op.create_unique_constraint('uq_rag_collections_qdrant_collection_name', 'rag_collections', ['qdrant_collection_name'])
    
    # Create rag_documents table
    op.create_table(
        'rag_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('file_type', sa.Text(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('vector_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_metadata', sa.Text(), nullable=True),
        sa.Column('uploaded_by', sa.String(length=36), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['collection_id'], ['rag_collections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for rag_documents
    op.create_index('ix_rag_documents_collection_id', 'rag_documents', ['collection_id'])
    op.create_index('ix_rag_documents_status', 'rag_documents', ['status'])
    op.create_index('ix_rag_documents_file_hash', 'rag_documents', ['file_hash'])
    
    # Create rag_search_history table
    op.create_table(
        'rag_search_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('search_metadata', sa.JSON(), nullable=True),
        sa.Column('execution_time', sa.Float(), nullable=True),
        sa.Column('retrieved_documents_count', sa.Integer(), nullable=True),
        sa.Column('reranked_documents_count', sa.Integer(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['collection_id'], ['rag_collections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for rag_search_history
    op.create_index('ix_rag_search_history_collection_id', 'rag_search_history', ['collection_id'])
    op.create_index('ix_rag_search_history_user_id', 'rag_search_history', ['user_id'])
    op.create_index('ix_rag_search_history_created_at', 'rag_search_history', ['created_at'])
    
    # Change column types to use enum types (remove default first, change type, then add default back)
    op.execute("ALTER TABLE rag_collections ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE rag_collections ALTER COLUMN status TYPE ragcollectionstatus USING status::ragcollectionstatus")
    op.execute("ALTER TABLE rag_collections ALTER COLUMN status SET DEFAULT 'active'::ragcollectionstatus")
    
    op.execute("ALTER TABLE rag_documents ALTER COLUMN file_type TYPE ragdocumenttype USING file_type::ragdocumenttype")
    
    op.execute("ALTER TABLE rag_documents ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE rag_documents ALTER COLUMN status TYPE ragdocumentstatus USING status::ragdocumentstatus")
    op.execute("ALTER TABLE rag_documents ALTER COLUMN status SET DEFAULT 'pending'::ragdocumentstatus")


def downgrade():
    # Drop tables in reverse order
    op.drop_table('rag_search_history')
    op.drop_table('rag_documents')
    op.drop_table('rag_collections')
    
    # Drop enum types using raw SQL
    op.execute("DROP TYPE IF EXISTS ragdocumenttype")
    op.execute("DROP TYPE IF EXISTS ragdocumentstatus")
    op.execute("DROP TYPE IF EXISTS ragcollectionstatus")