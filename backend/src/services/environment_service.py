"""
Environment Variable Service
Handles loading and merging of environment variables from different sources
"""

import os
from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.models.environment_variable import EnvironmentVariable
from src.models.user import User


class EnvironmentService:
    """Service for managing environment variables from multiple sources"""
    
    @staticmethod
    async def get_resolved_environment_variables(
        db: AsyncSession,
        user_id: str,
        workspace_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Get resolved environment variables with priority:
        1. DB workspace-specific variables (highest priority)
        2. DB global variables
        3. .env file variables (lowest priority)
        """
        resolved_vars: Dict[str, str] = {}
        
        # Start with .env file variables (lowest priority)
        env_file_vars = EnvironmentService._get_env_file_variables()
        resolved_vars.update(env_file_vars)
        
        # Add DB global variables (medium priority)
        global_vars = await EnvironmentService._get_db_global_variables(db, user_id)
        resolved_vars.update(global_vars)
        
        # Add DB workspace-specific variables (highest priority)
        if workspace_id:
            workspace_vars = await EnvironmentService._get_db_workspace_variables(
                db, user_id, workspace_id
            )
            resolved_vars.update(workspace_vars)
        
        return resolved_vars
    
    @staticmethod
    def _get_env_file_variables() -> Dict[str, str]:
        """Get environment variables from .env file and system environment"""
        env_vars = {}
        
        # Get all environment variables that start with common prefixes
        common_prefixes = [
            'VITE_',
            'OPENAI_',
            'ANTHROPIC_',
            'AZURE_',
            'GOOGLE_',
            'OLLAMA_',
            'API_',
            'DATABASE_',
            'REDIS_',
            'RABBITMQ_'
        ]
        
        for key, value in os.environ.items():
            # Include variables with common prefixes or custom user-defined ones
            if any(key.startswith(prefix) for prefix in common_prefixes) or key.isupper():
                env_vars[key] = value
        
        return env_vars
    
    @staticmethod
    async def _get_db_global_variables(
        db: AsyncSession, 
        user_id: str
    ) -> Dict[str, str]:
        """Get global environment variables from database"""
        query = select(EnvironmentVariable).where(
            and_(
                EnvironmentVariable.user_id == user_id,
                EnvironmentVariable.workspace_id.is_(None)
            )
        )
        
        result = await db.execute(query)
        env_vars = result.scalars().all()
        
        return {
            env_var.key: env_var.get_actual_value()
            for env_var in env_vars
            if env_var.value is not None
        }
    
    @staticmethod
    async def _get_db_workspace_variables(
        db: AsyncSession, 
        user_id: str, 
        workspace_id: str
    ) -> Dict[str, str]:
        """Get workspace-specific environment variables from database"""
        query = select(EnvironmentVariable).where(
            and_(
                EnvironmentVariable.user_id == user_id,
                EnvironmentVariable.workspace_id == workspace_id
            )
        )
        
        result = await db.execute(query)
        env_vars = result.scalars().all()
        
        return {
            env_var.key: env_var.get_actual_value()
            for env_var in env_vars
            if env_var.value is not None
        }
    
    @staticmethod
    async def get_available_environment_keys(
        db: AsyncSession,
        user_id: str,
        workspace_id: Optional[str] = None
    ) -> List[str]:
        """Get list of all available environment variable keys"""
        resolved_vars = await EnvironmentService.get_resolved_environment_variables(
            db, user_id, workspace_id
        )
        return list(resolved_vars.keys())
    
    @staticmethod
    def substitute_environment_variables(
        text: str,
        environment_vars: Dict[str, str]
    ) -> str:
        """
        Substitute environment variables in text using ${VAR_NAME} syntax
        
        Args:
            text: Text containing environment variable references
            environment_vars: Dictionary of environment variables
            
        Returns:
            Text with environment variables substituted
        """
        import re
        
        def replacer(match):
            var_name = match.group(1)
            return environment_vars.get(var_name, match.group(0))  # Return original if not found
        
        # Match ${VAR_NAME} pattern
        pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
        return re.sub(pattern, replacer, text)
    
    @staticmethod
    async def validate_environment_variable_key(
        db: AsyncSession,
        user_id: str,
        key: str,
        workspace_id: Optional[str] = None,
        exclude_id: Optional[str] = None
    ) -> bool:
        """Validate that environment variable key is unique in scope"""
        query = select(EnvironmentVariable).where(
            and_(
                EnvironmentVariable.user_id == user_id,
                EnvironmentVariable.key == key,
                EnvironmentVariable.workspace_id == workspace_id
            )
        )
        
        if exclude_id:
            query = query.where(EnvironmentVariable.id != exclude_id)
        
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        
        return existing is None


# Create singleton instance
environment_service = EnvironmentService()