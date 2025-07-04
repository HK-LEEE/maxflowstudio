#!/usr/bin/env python3
"""
Fix deployed_at timestamps for active deployments
이 스크립트는 현재 활성화된 배포들의 deployed_at 타임스탬프를 현재 시간으로 업데이트합니다.
"""

import asyncio
import sys
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update

# Add the src directory to Python path
sys.path.append('/home/lee/proejct/MAXFlowstudio/backend/src')

from models.api_deployment import ApiDeployment, DeploymentStatus

async def fix_deployed_at():
    """Fix deployed_at timestamps for active deployments."""
    
    # Database URL - adjust if needed
    DATABASE_URL = "sqlite+aiosqlite:///./flowstudio.db"
    
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Get all active deployments with null or old deployed_at
            query = select(ApiDeployment).where(
                ApiDeployment.status == DeploymentStatus.ACTIVE
            )
            result = await session.execute(query)
            deployments = result.scalars().all()
            
            current_time = datetime.utcnow()
            updated_count = 0
            
            for deployment in deployments:
                # Update deployed_at to current time for active deployments
                deployment.deployed_at = current_time
                updated_count += 1
                print(f"✅ Updated deployed_at for deployment: {deployment.name} (ID: {deployment.id})")
            
            if updated_count > 0:
                await session.commit()
                print(f"\n🎉 Successfully updated {updated_count} deployment(s)")
            else:
                print("📋 No deployments needed updating")
                
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(fix_deployed_at())