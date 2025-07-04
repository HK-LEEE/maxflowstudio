"""
Create Database Schema Script
Creates all tables defined in SQLAlchemy models
"""

import asyncio
import structlog
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from src.core.database import Base, get_database_url
from src.models import *  # Import all models to register them

logger = structlog.get_logger()


async def create_all_tables():
    """Create all tables defined in SQLAlchemy models"""
    
    database_url = get_database_url()
    logger.info("Creating database schema", database_url=database_url)
    
    # Create async engine
    engine = create_async_engine(database_url)
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            logger.info("Creating all tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("All tables created successfully")
            
        # Verify table creation
        async with engine.begin() as conn:
            logger.info("Verifying table creation...")
            
            # Get list of all tables
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in result.fetchall()]
            logger.info("Tables created", tables=tables)
            
            # Verify specific tables exist
            expected_tables = [
                'users',
                'flows', 
                'flow_studio_version',
                'workspaces',
                'workspace_permissions', 
                'flow_studio_workspace_map',
                'executions',
                'node_types',
                'api_keys',
                'api_deployments'
            ]
            
            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                logger.error("Missing expected tables", missing_tables=list(missing_tables))
            else:
                logger.info("All expected tables created successfully")
                
    except Exception as e:
        logger.error("Failed to create database schema", error=str(e))
        raise
    finally:
        await engine.dispose()


async def add_indexes():
    """Add performance optimization indexes"""
    
    database_url = get_database_url()
    engine = create_async_engine(database_url)
    
    indexes = [
        # Flow-related indexes
        "CREATE INDEX IF NOT EXISTS idx_flows_user_id ON flows(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_flows_created_at ON flows(created_at);",
        
        # Flow version indexes
        "CREATE INDEX IF NOT EXISTS idx_flow_versions_flow_id ON flow_studio_version(flow_id);",
        "CREATE INDEX IF NOT EXISTS idx_flow_versions_published ON flow_studio_version(is_published) WHERE is_published = true;",
        "CREATE INDEX IF NOT EXISTS idx_flow_versions_created_at ON flow_studio_version(created_at);",
        
        # Workspace indexes
        "CREATE INDEX IF NOT EXISTS idx_workspaces_creator ON workspaces(creator_user_id);",
        "CREATE INDEX IF NOT EXISTS idx_workspaces_type ON workspaces(type);",
        "CREATE INDEX IF NOT EXISTS idx_workspaces_active ON workspaces(is_active) WHERE is_active = true;",
        
        # Workspace permission indexes
        "CREATE INDEX IF NOT EXISTS idx_workspace_permissions_workspace ON workspace_permissions(workspace_id);",
        "CREATE INDEX IF NOT EXISTS idx_workspace_permissions_user ON workspace_permissions(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_workspace_permissions_group ON workspace_permissions(group_id);",
        
        # Flow workspace mapping indexes
        "CREATE INDEX IF NOT EXISTS idx_flow_workspace_map_workspace ON flow_studio_workspace_map(workspace_id);",
        
        # Execution indexes
        "CREATE INDEX IF NOT EXISTS idx_executions_flow_id ON executions(flow_id);",
        "CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status);",
        "CREATE INDEX IF NOT EXISTS idx_executions_created_at ON executions(created_at);",
        
        # API deployment indexes
        "CREATE INDEX IF NOT EXISTS idx_api_deployments_flow_id ON api_deployments(flow_id);",
        "CREATE INDEX IF NOT EXISTS idx_api_deployments_active ON api_deployments(is_active) WHERE is_active = true;",
    ]
    
    try:
        async with engine.begin() as conn:
            logger.info("Creating performance indexes...")
            
            for index_sql in indexes:
                try:
                    await conn.execute(text(index_sql))
                    logger.debug("Created index", sql=index_sql)
                except Exception as e:
                    logger.warning("Failed to create index", sql=index_sql, error=str(e))
            
            logger.info("Performance indexes created successfully")
            
    except Exception as e:
        logger.error("Failed to create indexes", error=str(e))
        raise
    finally:
        await engine.dispose()


async def verify_constraints():
    """Verify database constraints and relationships"""
    
    database_url = get_database_url()
    engine = create_async_engine(database_url)
    
    try:
        async with engine.begin() as conn:
            logger.info("Verifying database constraints...")
            
            # Check foreign key constraints
            constraint_checks = [
                "SELECT COUNT(*) FROM flows f LEFT JOIN users u ON f.user_id = u.id WHERE u.id IS NULL;",
                "SELECT COUNT(*) FROM flow_studio_version fv LEFT JOIN flows f ON fv.flow_id = f.id WHERE f.id IS NULL;",
                "SELECT COUNT(*) FROM workspace_permissions wp LEFT JOIN workspaces w ON wp.workspace_id = w.id WHERE w.id IS NULL;",
                "SELECT COUNT(*) FROM flow_studio_workspace_map fm LEFT JOIN flows f ON fm.flow_id = f.id WHERE f.id IS NULL;",
                "SELECT COUNT(*) FROM flow_studio_workspace_map fm LEFT JOIN workspaces w ON fm.workspace_id = w.id WHERE w.id IS NULL;"
            ]
            
            for check_sql in constraint_checks:
                result = await conn.execute(text(check_sql))
                orphan_count = result.scalar()
                if orphan_count > 0:
                    logger.warning("Found orphaned records", sql=check_sql, count=orphan_count)
                else:
                    logger.debug("Constraint check passed", sql=check_sql)
            
            # Check unique constraints
            unique_checks = [
                ("flow_studio_workspace_map", "flow_id", "Flows should have unique workspace mapping"),
            ]
            
            for table, column, description in unique_checks:
                result = await conn.execute(text(f"""
                    SELECT {column}, COUNT(*) as cnt 
                    FROM {table} 
                    GROUP BY {column} 
                    HAVING COUNT(*) > 1;
                """))
                
                duplicates = result.fetchall()
                if duplicates:
                    logger.warning("Found duplicate values", table=table, column=column, duplicates=duplicates)
                else:
                    logger.debug("Unique constraint verified", description=description)
            
            logger.info("Database constraint verification completed")
            
    except Exception as e:
        logger.error("Failed to verify constraints", error=str(e))
        raise
    finally:
        await engine.dispose()


async def main():
    """Main function to create database schema"""
    
    logger.info("Starting database schema creation...")
    
    try:
        # Step 1: Create all tables
        await create_all_tables()
        
        # Step 2: Add performance indexes
        await add_indexes()
        
        # Step 3: Verify constraints
        await verify_constraints()
        
        logger.info("Database schema creation completed successfully!")
        
    except Exception as e:
        logger.error("Database schema creation failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())