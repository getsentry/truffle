#!/usr/bin/env python3
"""
Reset database by dropping all tables and optionally recreating them.

Usage:
  python scripts/reset_db.py                    # Drop and recreate tables
  python scripts/reset_db.py --drop-only        # Only drop tables
  python scripts/reset_db.py --import-skills    # Drop, recreate, and import skills
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from database import create_tables, drop_tables
from main import auto_import_skills


async def reset_database(drop_only: bool = False, import_skills: bool = False):
    """Reset the database by dropping and optionally recreating tables"""

    print("🗑️  Dropping all database tables...")
    await drop_tables()
    print("✅ All tables dropped")

    if drop_only:
        print("🏁 Database reset complete (drop-only mode)")
        return

    print("🔨 Creating database tables...")
    await create_tables()
    print("✅ Database tables created")

    if import_skills:
        print("📥 Importing skills from JSON files...")
        await auto_import_skills()
        print("✅ Skills imported")

    print("🏁 Database reset complete!")


async def main():
    """Main function with argument parsing"""
    import argparse

    parser = argparse.ArgumentParser(description="Reset database")
    parser.add_argument(
        "--drop-only", action="store_true", help="Only drop tables, don't recreate"
    )
    parser.add_argument(
        "--import-skills",
        action="store_true",
        help="Import skills after recreating tables",
    )

    args = parser.parse_args()

    # Confirmation prompt for safety
    if args.drop_only:
        confirm_msg = "This will DROP ALL TABLES. Are you sure? (y/N): "
    else:
        confirm_msg = "This will RESET THE DATABASE. Are you sure? (y/N): "

    response = input(confirm_msg)
    if response.lower() not in ["y", "yes"]:
        print("❌ Operation cancelled")
        return

    await reset_database(drop_only=args.drop_only, import_skills=args.import_skills)


if __name__ == "__main__":
    asyncio.run(main())
