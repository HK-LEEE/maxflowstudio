"""
Enhanced Migration script to move existing flows to workspaces
Run this script after deploying workspace models to migrate existing flows
"""

import asyncio
import uuid
import structlog
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from src.core.database import AsyncSessionLocal
from src.models.user import User
from src.models.flow import Flow, FlowVersion
from src.models.workspace import Workspace, WorkspaceType
from src.models.workspace_permission import WorkspacePermission, PermissionType
from src.models.flow_workspace_map import FlowWorkspaceMap
from src.services.workspace_service import workspace_service

logger = structlog.get_logger()


async def migrate_flows_to_workspaces():
    """Migrate existing flows to user workspaces."""
    
    async with AsyncSessionLocal() as db:
        logger.info("Starting flow to workspace migration...")
        
        # Get all users
        users_result = await db.execute(select(User))
        users = users_result.scalars().all()
        
        logger.info("Found users for migration", user_count=len(users))
        
        # Create default workspaces for each user
        user_workspaces = {}
        
        for user in users:
            logger.info("Processing user", username=user.username, user_id=user.id)
            
            # Check if user already has a workspace
            existing_workspaces_result = await db.execute(
                select(Workspace).where(
                    Workspace.creator_user_id == user.id,
                    Workspace.type == WorkspaceType.USER
                )
            )
            existing_workspace = existing_workspaces_result.scalar_one_or_none()
            
            if existing_workspace:
                logger.info("User already has workspace", 
                          username=user.username, 
                          workspace_name=existing_workspace.name)
                user_workspaces[user.id] = existing_workspace
            else:
                # Create default workspace for user
                try:
                    workspace = await workspace_service.create_default_workspace_for_user(
                        db=db,
                        user_id=user.id,
                        username=user.username
                    )
                    user_workspaces[user.id] = workspace
                    logger.info("Created workspace for user", 
                              username=user.username, 
                              workspace_name=workspace.name)
                except Exception as e:
                    logger.error("Failed to create workspace", 
                               username=user.username, 
                               error=str(e))
                    continue
        
        # Get all flows that are not yet assigned to workspaces
        flows_result = await db.execute(
            select(Flow).outerjoin(FlowWorkspaceMap).where(
                FlowWorkspaceMap.flow_id.is_(None)
            )
        )
        unassigned_flows = flows_result.scalars().all()
        
        logger.info("Found unassigned flows", count=len(unassigned_flows))
        
        # Assign flows to their owner's workspace
        migration_count = 0
        
        for flow in unassigned_flows:
            if flow.user_id in user_workspaces:
                workspace = user_workspaces[flow.user_id]
                
                # Create flow-workspace mapping
                flow_map = FlowWorkspaceMap(
                    id=str(uuid.uuid4()),
                    flow_id=flow.id,
                    workspace_id=workspace.id
                )
                
                db.add(flow_map)
                migration_count += 1
                
                logger.info("Assigned flow to workspace", 
                          flow_name=flow.name, 
                          workspace_name=workspace.name)
            else:
                logger.warning("No workspace found for flow", 
                             flow_name=flow.name, 
                             user_id=flow.user_id)
        
        await db.commit()
        
        logger.info("Flow migration completed", 
                   workspaces_created=len(user_workspaces),
                   flows_migrated=migration_count)
        
        # Verify migration
        total_flows_result = await db.execute(select(Flow))
        total_flows = len(total_flows_result.scalars().all())
        
        assigned_flows_result = await db.execute(select(FlowWorkspaceMap))
        assigned_flows = len(assigned_flows_result.scalars().all())
        
        logger.info("Migration verification", 
                   assigned_flows=assigned_flows,
                   total_flows=total_flows)
        
        if assigned_flows < total_flows:
            logger.warning("Some flows remain unassigned - manual intervention may be required")


async def create_admin_workspace():
    """Create a special admin workspace for superusers."""
    
    async with AsyncSessionLocal() as db:
        print("Creating admin workspace...")
        
        # Get first superuser
        admin_result = await db.execute(
            select(User).where(User.is_superuser == True)
        )
        admin_user = admin_result.scalar_one_or_none()
        
        if not admin_user:
            print("No admin user found. Skipping admin workspace creation.")
            return
        
        # Check if admin workspace already exists
        admin_workspace_result = await db.execute(
            select(Workspace).where(
                Workspace.name == "Admin Workspace",
                Workspace.type == WorkspaceType.USER
            )
        )
        existing_admin_workspace = admin_workspace_result.scalar_one_or_none()
        
        if existing_admin_workspace:
            print("Admin workspace already exists.")
            return
        
        # Create admin workspace
        admin_workspace = await workspace_service.create_workspace(
            db=db,
            name="Admin Workspace",
            creator_user_id=admin_user.id,
            workspace_type=WorkspaceType.USER,
            description="Administrative workspace for system management"
        )
        
        print(f"Created admin workspace: {admin_workspace.name}")


async def create_initial_flow_versions():
    """Create initial versions for existing flows that don't have versions."""
    
    async with AsyncSessionLocal() as db:
        logger.info("Creating initial versions for existing flows...")
        
        # Get all flows
        flows_result = await db.execute(select(Flow))
        flows = flows_result.scalars().all()
        
        logger.info("Found flows for version creation", flow_count=len(flows))
        
        version_count = 0
        
        for flow in flows:
            # Check if flow already has versions
            versions_result = await db.execute(
                select(FlowVersion).where(FlowVersion.flow_id == flow.id)
            )
            existing_versions = versions_result.scalars().all()
            
            if not existing_versions:
                # Create initial version
                initial_version = FlowVersion(
                    id=str(uuid.uuid4()),
                    flow_id=flow.id,
                    version_number=1,
                    version_name="Initial Version",
                    description="Initial version created during migration",
                    definition={"nodes": [], "edges": []},  # Empty definition for existing flows
                    is_published=False,
                    change_summary="Initial version created during data migration",
                    created_by=flow.user_id,
                    created_at=flow.created_at
                )
                
                db.add(initial_version)
                version_count += 1
                
                logger.info("Created initial version for flow", 
                          flow_name=flow.name, 
                          flow_id=flow.id)
        
        await db.commit()
        
        logger.info("Initial version creation completed", 
                   versions_created=version_count)


async def main():
    """Main migration function."""
    try:
        logger.info("=" * 60)
        logger.info("MAX Flowstudio - Enhanced Database Migration")
        logger.info("=" * 60)
        
        # Run migrations in order
        await migrate_flows_to_workspaces()
        await create_admin_workspace()
        await create_initial_flow_versions()
        
        logger.info("=" * 60)
        logger.info("Migration completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("Migration failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())