"""
Database Node Worker
"""

import json
from typing import Dict, Any, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .base_worker import BaseWorker, ExecutionContext


class DatabaseWorker(BaseWorker):
    """Worker for database operations"""
    
    async def execute(
        self,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute database queries
        """
        self.logger.info("Executing database node", node_id=context.node_id)
        
        # Get configuration
        operation = config.get('operation', 'select').lower()
        table = config.get('table', '')
        query = config.get('query', '')
        connection_string = config.get('connection_string')
        
        # Get input values
        params = inputs.get('params', {})
        
        if not connection_string:
            # Try to get from environment or use default
            import os
            connection_string = os.getenv('DATABASE_URL')
            if not connection_string:
                raise ValueError("Database connection string is required")
        
        if not query:
            if table and operation == 'select':
                query = f"SELECT * FROM {table}"
            else:
                raise ValueError("Query is required in configuration")
        
        try:
            # Create async engine
            engine = create_async_engine(connection_string)
            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            
            async with async_session() as session:
                # Execute query
                self.logger.info(
                    "Executing database query",
                    node_id=context.node_id,
                    operation=operation
                )
                
                result_proxy = await session.execute(text(query), params)
                
                # Handle different operations
                if operation in ['select', 'SELECT']:
                    rows = result_proxy.fetchall()
                    result = [dict(row._mapping) for row in rows]
                    count = len(result)
                    
                elif operation in ['insert', 'INSERT', 'update', 'UPDATE', 'delete', 'DELETE']:
                    await session.commit()
                    result = {"affected_rows": result_proxy.rowcount}
                    count = result_proxy.rowcount
                    
                else:
                    result = {"message": "Query executed successfully"}
                    count = 0
                
                self.logger.info(
                    "Database query completed",
                    node_id=context.node_id,
                    row_count=count
                )
                
                return self.format_output(
                    result=result,
                    count=count,
                    error=None
                )
                
        except Exception as e:
            self.logger.error(
                "Database query failed",
                node_id=context.node_id,
                error=str(e)
            )
            return self.format_output(
                result=None,
                count=0,
                error=str(e)
            )
        finally:
            if 'engine' in locals():
                await engine.dispose()