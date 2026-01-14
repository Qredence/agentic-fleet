#!/usr/bin/env python3
"""Chunk large memory files and index to Chroma Cloud."""

import hashlib
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # Project root
CONTEXT_DIR = BASE_DIR / ".fleet" / "context"

MAX_CHUNK_SIZE = 14000

CHUNK_DIR = CONTEXT_DIR / ".chunks"
CHUNK_DIR.mkdir(exist_ok=True)


def chunk_markdown(content: str, max_size: int = MAX_CHUNK_SIZE) -> list[dict]:
    """Split markdown into overlapping chunks."""
    chunks = []
    lines = content.split("\n")
    current_chunk = []
    current_size = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        line_size = len(line) + 1

        if current_size + line_size > max_size and current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]

            chunk = {
                "id": f"chunk_{chunk_hash}",
                "content": chunk_text,
                "metadata": {
                    "start_line": i - len(current_chunk),
                    "end_line": i - 1,
                },
            }
            chunks.append(chunk)

            overlap_start = max(0, len(current_chunk) - 3)
            current_chunk = current_chunk[overlap_start:]
            current_size = sum(len(line) + 1 for line in current_chunk)

        current_chunk.append(line)
        current_size += line_size
        i += 1

    if current_chunk:
        chunk_text = "\n".join(current_chunk)
        chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
        chunks.append(
            {
                "id": f"chunk_{chunk_hash}",
                "content": chunk_text,
                "metadata": {"start_line": i - len(current_chunk), "end_line": i - 1},
            }
        )

    return chunks


def index_file_to_chroma(file_path: Path, collection, max_chunk_size: int = MAX_CHUNK_SIZE):
    """Index a single file to Chroma, chunking if necessary."""
    content = file_path.read_text()
    file_size = len(content)

    name = file_path.stem

    if file_size <= max_chunk_size:
        doc_id = hashlib.md5(content.encode()).hexdigest()[:16]
        collection.upsert(
            documents=[content],
            ids=[doc_id],
            metadatas=[{"source": str(file_path), "name": name, "type": "full"}],
        )
        print(f"  ✓ {name} ({file_size} bytes) - indexed as single document")
        return 1
    else:
        chunks = chunk_markdown(content, max_chunk_size)
        doc_ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            doc_id = f"{name}_{chunk['id']}"
            doc_ids.append(doc_id)
            documents.append(chunk["content"])
            metadatas.append(
                {
                    "source": str(file_path),
                    "name": name,
                    "type": "chunk",
                    "chunk_index": chunk["id"],
                    "start_line": chunk["metadata"]["start_line"],
                    "end_line": chunk["metadata"]["end_line"],
                }
            )

        collection.upsert(documents=documents, ids=doc_ids, metadatas=metadatas)
        print(f"  ✓ {name} ({file_size} bytes) - indexed as {len(chunks)} chunks")
        return len(chunks)


def main():
    """Index memory files to Chroma Cloud."""
    from chroma_driver import ChromaDriver

    print("=" * 60)
    print("Chunking and Indexing Memories to Chroma Cloud")
    print("=" * 60)

    driver = ChromaDriver()
    if not driver.client:
        print("ERROR: Could not connect to Chroma Cloud")
        sys.exit(1)

    procedural = driver.collections.get("procedural")
    semantic = driver.collections.get("semantic")

    if not procedural or not semantic:
        print("ERROR: Could not access collections")
        sys.exit(1)

    files_to_index = [
        (CONTEXT_DIR / "skills" / "dspy-agent-framework-integration.md", procedural),
        (CONTEXT_DIR / "blocks" / "project" / "architecture.md", semantic),
        (CONTEXT_DIR / "blocks" / "project" / "conventions.md", semantic),
        (CONTEXT_DIR / "blocks" / "project" / "commands.md", semantic),
        (CONTEXT_DIR / "blocks" / "project" / "gotchas.md", semantic),
        (CONTEXT_DIR / "blocks" / "workflows" / "git.md", semantic),
        (CONTEXT_DIR / "blocks" / "workflows" / "review.md", semantic),
        (CONTEXT_DIR / "blocks" / "decisions" / "001-memory-system.md", semantic),
        (CONTEXT_DIR / "MEMORY.md", procedural),
        (CONTEXT_DIR / "skills" / "memory-system-guide.md", procedural),
    ]

    total_chunks = 0

    for file_path, collection in files_to_index:
        if not file_path.exists():
            print(f"  ✗ {file_path.name} - not found")
            continue

        count = index_file_to_chroma(file_path, collection)
        total_chunks += count

    print("=" * 60)
    print(f"Indexed {total_chunks} document(s) to Chroma Cloud")
    print("=" * 60)


if __name__ == "__main__":
    main()
