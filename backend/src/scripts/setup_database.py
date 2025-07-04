"""
Complete Database Setup Script
Creates schema, runs migrations, and verifies everything
"""

import asyncio
import structlog
import sys
import os

# Add src to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from create_database_schema import create_all_tables, add_indexes, verify_constraints
from migrate_flows_to_workspaces import main as run_migration

logger = structlog.get_logger()


async def setup_complete_database():
    """Complete database setup process"""
    
    logger.info("Starting complete database setup...")
    
    try:
        # Step 1: Create all tables and schema
        logger.info("Step 1: Creating database schema...")
        await create_all_tables()
        
        # Step 2: Add performance indexes
        logger.info("Step 2: Adding performance indexes...")
        await add_indexes()
        
        # Step 3: Run data migrations
        logger.info("Step 3: Running data migrations...")
        await run_migration()
        
        # Step 4: Verify database integrity
        logger.info("Step 4: Verifying database constraints...")
        await verify_constraints()
        
        logger.info("✅ Complete database setup finished successfully!")
        
        # Print summary
        logger.info("Database setup summary:")
        logger.info("- ✅ All tables created")
        logger.info("- ✅ Performance indexes added")
        logger.info("- ✅ Existing data migrated")
        logger.info("- ✅ Database constraints verified")
        logger.info("")
        logger.info("🚀 MAX Flowstudio database is ready!")
        
    except Exception as e:
        logger.error("❌ Database setup failed", error=str(e))
        raise


async def main():
    """Main function"""
    logger.info("=" * 80)
    logger.info("MAX Flowstudio - Complete Database Setup")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This script will:")
    logger.info("1. Create all database tables and schema")
    logger.info("2. Add performance optimization indexes")
    logger.info("3. Migrate existing data to new structure")
    logger.info("4. Verify database integrity")
    logger.info("")
    logger.info("=" * 80)
    
    try:
        await setup_complete_database()
    except Exception as e:
        logger.error("Setup failed - please check the logs above", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())