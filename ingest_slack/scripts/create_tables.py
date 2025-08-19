#!/usr/bin/env python3
"""Create database tables"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from database import create_tables


async def main():
    """Create all database tables"""
    print("Creating database tables...")
    await create_tables()
    print("✅ Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(main())
