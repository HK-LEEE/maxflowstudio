#!/usr/bin/env python3
"""
Database verification script
"""

import asyncio
from sqlalchemy import text
from src.core.database import AsyncSessionLocal, get_database_url


async def verify_database():
    print(f'Database URL: {get_database_url()}')
    print()
    
    async with AsyncSessionLocal() as session:
        # Show all tables
        result = await session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """))
        tables = result.fetchall()
        
        print('=== Created Tables ===')
        for table in tables:
            print(f'  {table[0]}')
        
        print()
        
        # Show all indexes
        result = await session.execute(text("""
            SELECT 
                schemaname,
                tablename, 
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """))
        indexes = result.fetchall()
        
        print('=== Created Indexes ===')
        current_table = None
        for idx in indexes:
            if current_table != idx[1]:
                current_table = idx[1]
                print(f'  Table: {current_table}')
            print(f'    {idx[2]}')
        
        print()
        print(f'Total Tables: {len(tables)}')
        print(f'Total Indexes: {len(indexes)}')


if __name__ == "__main__":
    asyncio.run(verify_database())