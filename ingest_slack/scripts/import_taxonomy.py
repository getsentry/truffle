#!/usr/bin/env python3
"""
Import taxonomy from JSON files into the database.

Usage:
  python scripts/import_taxonomy.py                    # Import all domains
  python scripts/import_taxonomy.py engineering.json  # Import specific file
  python scripts/import_taxonomy.py --validate        # Validate only, don't import
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from services.storage_service import StorageService


async def import_taxonomy_files(
    skills_dir: Path = Path("skills"),
    validate_only: bool = False,
    specific_file: str | None = None,
):
    """Import all JSON files from skills directory"""
    storage = StorageService()

    if specific_file:
        # Import only specific file
        json_files = [skills_dir / specific_file]
    else:
        # Import all JSON files
        json_files = list(skills_dir.glob("*.json"))

    total_skills = 0

    for json_file in json_files:
        if not json_file.exists():
            print(f"❌ File not found: {json_file}")
            continue

        print(f"Processing {json_file.name}...")

        try:
            # Load and validate JSON
            data = json.loads(json_file.read_text())
            validate_taxonomy_file(data, json_file.name)

            # Convert to database format
            skills_data = []
            for skill in data["skills"]:
                skills_data.append(
                    {
                        "skill_key": skill["key"],
                        "name": skill["name"],
                        "domain": data["domain"],
                        "aliases": json.dumps(skill["aliases"]),  # Store as JSON string
                    }
                )

            if not validate_only:
                # Import to database
                await storage.upsert_skills(skills_data)
                print(
                    f"  ✅ Imported {len(skills_data)} skills from {data['domain']} domain"
                )
            else:
                print(
                    f"  ✓ Validated {len(skills_data)} skills from {data['domain']} domain"
                )

            total_skills += len(skills_data)

        except Exception as e:
            print(f"  ❌ Error processing {json_file.name}: {e}")
            continue

    action = "validated" if validate_only else "imported"
    print(
        f"\n🎉 {action.title()} {total_skills} total skills from {len(json_files)} files"
    )


def validate_taxonomy_file(data: dict[str, Any], filename: str):
    """Validate JSON structure"""
    required_fields = ["domain", "skills"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field '{field}'")

    if not isinstance(data["skills"], list):
        raise ValueError("'skills' must be a list")

    for i, skill in enumerate(data["skills"]):
        skill_required = ["key", "name", "aliases"]
        for field in skill_required:
            if field not in skill:
                raise ValueError(f"Skill {i} missing required field '{field}'")

        if not isinstance(skill["aliases"], list):
            raise ValueError(f"Skill {i} 'aliases' must be a list")

        # Validate key format (no spaces, lowercase, etc.)
        if not skill["key"] or not isinstance(skill["key"], str):
            raise ValueError(f"Skill {i} 'key' must be a non-empty string")


async def main():
    """Main entry point with argument parsing"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Import taxonomy JSON files to database"
    )
    parser.add_argument("file", nargs="?", help="Specific file to import (optional)")
    parser.add_argument(
        "--validate", action="store_true", help="Validate only, don't import"
    )
    parser.add_argument(
        "--skills-dir", default="skills", help="Directory containing JSON files"
    )

    args = parser.parse_args()

    skills_dir = Path(args.skills_dir)
    if not skills_dir.exists():
        print(f"❌ Skills directory not found: {skills_dir}")
        return 1

    await import_taxonomy_files(
        skills_dir=skills_dir, validate_only=args.validate, specific_file=args.file
    )

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
