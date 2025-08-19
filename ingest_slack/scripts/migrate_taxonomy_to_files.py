#!/usr/bin/env python3
"""Extract current hardcoded taxonomy to JSON files"""

import json
import sys
from collections import defaultdict
from pathlib import Path

# Add parent directory to path to import taxonomy
sys.path.append(str(Path(__file__).parent.parent))

from taxonomy import SKILLS


def extract_to_files():
    """Extract current SKILLS to domain-based JSON files"""
    skills_dir = Path("skills")
    skills_dir.mkdir(exist_ok=True)

    # Group skills by domain
    domains = defaultdict(list)
    for skill in SKILLS:
        domains[skill.domain].append(
            {"key": skill.key, "name": skill.name, "aliases": list(skill.aliases)}
        )

    # Write each domain to separate file
    for domain, skills in domains.items():
        domain_data = {"domain": domain, "skills": skills}

        output_file = skills_dir / f"{domain}.json"
        output_file.write_text(json.dumps(domain_data, indent=2))
        print(f"✅ Created {output_file} with {len(skills)} skills")

    print(
        f"\n🎉 Migration complete! Created {len(domains)} domain files in skills/ directory"
    )


if __name__ == "__main__":
    extract_to_files()
