#!/usr/bin/env python3
"""Learn a new skill - integrates NeonDB (structured) + ChromaDB (semantic)."""

import os
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

# Setup paths
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
os.chdir(Path(__file__).resolve().parent.parent.parent.parent)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract frontmatter and body from markdown."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                metadata = yaml.safe_load(parts[1].strip())
            except yaml.YAMLError:
                metadata = {}
            return metadata, parts[2].strip()
    return {}, content


def serialize_metadata(metadata: dict) -> dict:
    """Convert metadata values to JSON-serializable types."""
    result = {}
    for key, value in metadata.items():
        if isinstance(value, (date, datetime)):
            result[key] = value.isoformat()
        elif isinstance(value, list):
            result[key] = [str(v) if isinstance(v, (date, datetime)) else v for v in value]
        else:
            result[key] = value
    return result


def load_neon_config():
    """Load NeonDB config."""
    config_path = ".fleet/context/.neon/config.yaml"
    if not Path(config_path).exists():
        print(f"ERROR: NeonDB config not found at {config_path}")
        return None
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_chroma_config():
    """Load ChromaDB config."""
    config_path = ".fleet/context/.chroma/config.yaml"
    if not Path(config_path).exists():
        print(f"ERROR: ChromaDB config not found at {config_path}")
        return None
    with open(config_path) as f:
        return yaml.safe_load(f)


def learn_skill(file_path: str):
    """Learn a skill - store in NeonDB and index to ChromaDB."""
    from neon_memory import NeonMemory

    path = Path(file_path)
    if not path.exists():
        print(f"ERROR: File not found: {file_path}")
        return False

    content = path.read_text()
    metadata, body = parse_frontmatter(content)

    # Determine skill name: prefer frontmatter 'name' or 'title',
    # then parent directory name (for SKILL.md format), then filename stem
    name_from_meta = metadata.get("name")
    title_from_meta = metadata.get("title")

    if name_from_meta:
        skill_name = str(name_from_meta)
    elif title_from_meta:
        skill_name = str(title_from_meta).lower().replace(" ", "-")
    elif path.stem.lower() == "skill" and path.parent.name != "skills":
        # Format: .fleet/context/skills/{skill-name}/SKILL.md
        skill_name = path.parent.name
    else:
        skill_name = path.stem

    category = metadata.get("category", metadata.get("scope", "general"))
    description = metadata.get("description", "")

    print(f"\n{'=' * 60}")
    print(f"LEARNING SKILL: {skill_name}")
    print(f"{'=' * 60}")

    # 1. Save to NeonDB (structured storage)
    print("\n[1/2] Saving to NeonDB...")
    try:
        memory = NeonMemory()
        # Serialize metadata to handle date objects
        safe_metadata = serialize_metadata(
            {
                "source_file": str(path),
                "learned_at": datetime.now().isoformat(),
                **metadata,
            }
        )
        memory.save_skill(
            skill_name=skill_name,
            category=category,
            description=description,
            implementation=body[:5000] if len(body) > 5000 else body,
            metadata=safe_metadata,
        )
        print(f"  ✓ Saved to NeonDB: {skill_name}")
        memory._close()
    except Exception as e:
        print(f"  ✗ NeonDB error: {e}")
        return False

    # 2. Index to ChromaDB (semantic storage)
    print("\n[2/2] Indexing to ChromaDB...")
    try:
        chroma_config = load_chroma_config()
        if not chroma_config:
            print("  ⚠ Skipping ChromaDB (no config)")
            return True

        cloud = chroma_config.get("cloud", {})
        collections = chroma_config.get("collections", {})

        import chromadb

        client = chromadb.CloudClient(
            tenant=cloud.get("tenant"), database=cloud.get("database"), api_key=cloud.get("api_key")
        )

        procedural_name = collections.get("procedural", "agentic-fleet-procedural")
        collection = client.get_or_create_collection(name=procedural_name)

        doc_id = f"skill_{skill_name.replace(' ', '_').lower()}"
        collection.upsert(
            documents=[body],
            ids=[doc_id],
            metadatas=[
                {
                    "source": str(path),
                    "name": skill_name,
                    "type": "skill",
                    "category": category,
                    "description": description,
                    "learned_at": datetime.now().isoformat(),
                }
            ],
        )
        print(f"  ✓ Indexed to ChromaDB: {doc_id}")

    except Exception as e:
        print(f"  ⚠ ChromaDB warning: {e}")

    print(f"\n{'=' * 60}")
    print(f"SKILL LEARNED: {skill_name}")
    print(f"  Category: {category}")
    print("  NeonDB: tracking usage & success rate")
    print("  ChromaDB: semantic search enabled")
    print(f"{'=' * 60}\n")
    return True


def main():
    """Run skill learning CLI."""
    if len(sys.argv) < 2:
        print("Usage: uv run python neon_learn.py <skill-file.md>")
        print("Example: uv run python neon_learn.py .fleet/context/skills/my-skill.md")
        sys.exit(1)

    file_path = sys.argv[1]
    success = learn_skill(file_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
