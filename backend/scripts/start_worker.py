#!/usr/bin/env python3
"""
Start Worker Script
Usage: python scripts/start_worker.py
"""

import sys
import os
import asyncio

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.worker_service import main

if __name__ == "__main__":
    print("Starting MAX Flowstudio Worker Service...")
    asyncio.run(main())