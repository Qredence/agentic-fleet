#!/usr/bin/env python3
"""Recall information - searches both NeonDB (structured) and ChromaDB (semantic)."""

import os
import sys
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
os.chdir(Path(__file__).resolve().parent.parent.parent.parent)


def load_neon_config():
    """Load NeonDB config."""
    config_path = ".fleet/context/.neon/config.yaml"
    if not Path(config_path).exists():
        return None
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_chroma_config():
    """Load ChromaDB config."""
    config_path = ".fleet/context/.chroma/config.yaml"
    if not Path(config_path).exists():
        return None
    with open(config_path) as f:
        return yaml.safe_load(f)


def recall(query: str, limit: int = 5):
    """Recall information from both NeonDB and ChromaDB."""
    from neon_memory import NeonMemory

    print(f"\n{'=' * 60}")
    print(f"RECALL: {query}")
    print(f"{'=' * 60}\n")

    # 1. Search NeonDB structured data
    print("[1/2] Searching NeonDB (structured)...")
    try:
        memory = NeonMemory()
        skills = memory.list_skills()

        # Filter skills by name/category match
        query_lower = query.lower()
        matching_skills = [
            s
            for s in skills
            if query_lower in s.get("skill_name", "").lower()
            or query_lower in s.get("category", "").lower()
            or query_lower in s.get("description", "").lower()
        ]

        if matching_skills:
            print("\n  Skills found in NeonDB:")
            for skill in matching_skills[:limit]:
                print(f"    - {skill['skill_name']} ({skill['category']})")
                print(f"      Usage: {skill['usage_count']}, Success: {skill['success_rate']:.1%}")
                if skill.get("description"):
                    print(f"      {skill['description'][:100]}...")
        else:
            print("  No matching skills in NeonDB")

        # Get recent sessions
        sessions = memory.list_sessions(limit=3)
        if sessions:
            print(f"\n  Recent sessions: {len(sessions)}")
            for s in sessions:
                print(f"    - {s['session_id'][:8]}... ({s['status']})")

        memory._close()
    except Exception as e:
        print(f"  ⚠ NeonDB error: {e}")

    # 2. Search ChromaDB semantic memory
    print("\n[2/2] Searching ChromaDB (semantic)...")
    try:
        chroma_config = load_chroma_config()
        if not chroma_config:
            print("  ⚠ ChromaDB config not found")
            return

        cloud = chroma_config.get("cloud", {})
        collections = chroma_config.get("collections", {})

        import chromadb

        client = chromadb.CloudClient(
            tenant=cloud.get("tenant"), database=cloud.get("database"), api_key=cloud.get("api_key")
        )

        # Search all collections
        all_results = {}
        collection_names = [
            ("procedural", collections.get("procedural")),
            ("semantic", collections.get("semantic")),
        ]

        for coll_key, coll_name in collection_names:
            if not coll_name:
                continue
            try:
                collection = client.get_collection(name=coll_name)
                results = collection.query(query_texts=[query], n_results=limit)
                if results["documents"]:
                    all_results[coll_key] = results
            except Exception as e:
                print(f"  ⚠ Collection {coll_key}: {e}")

        if all_results:
            for coll_key, results in all_results.items():
                print(f"\n  {coll_key.upper()} collection:")
                for i, (doc, meta) in enumerate(
                    zip(results["documents"][0], results["metadatas"][0], strict=True)
                ):
                    name = meta.get("name", meta.get("source", "Unknown"))
                    print(f"\n    [{i + 1}] {name}")
                    print(f"        Type: {meta.get('type', 'unknown')}")
                    if meta.get("category"):
                        print(f"        Category: {meta['category']}")
                    if meta.get("description"):
                        print(f"        Description: {meta['description'][:100]}...")
                    print("        ---")
                    print(f"        {doc[:200]}...")
        else:
            print("  No semantic matches found")

    except Exception as e:
        print(f"  ⚠ ChromaDB error: {e}")

    print(f"\n{'=' * 60}\n")


def main():
    """Run recall CLI."""
    if len(sys.argv) < 2:
        print('Usage: uv run python neon_recall.py "search query"')
        print('Example: uv run python neon_recall.py "DSPy typed signatures"')
        sys.exit(1)

    query = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    recall(query, limit)


if __name__ == "__main__":
    main()
