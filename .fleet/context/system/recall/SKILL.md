---
name: recall
description: Semantic search for memory. Use to find solutions, patterns, or context from Chroma Cloud.
---

# Recall Memory

This skill allows you to search your memory system using semantic queries.

## Workflow

1.  **Formulate Your Query**:
    Think about what you're trying to find:
    - A solution to a specific problem (e.g., "How do I fix CORS errors?")
    - A pattern or best practice (e.g., "Python async patterns")
    - Historical context (e.g., "What did we decide about routing?")

2.  **Run the Search**:
    Execute the memory manager recall command:

    ```bash
    uv run python .fleet/context/scripts/memory_manager.py recall "<your query>"
    ```

    Example:

    ```bash
    uv run python .fleet/context/scripts/memory_manager.py recall "memory system implementation"
    ```

3.  **Review Results**:
    The system will return:
    - **Top matches** from semantic memory (facts, decisions)
    - **Relevant skills** from procedural memory (how-tos)
    - **Similarity scores** to gauge relevance
    - **Source metadata** (file paths, timestamps)

4.  **Refine if Needed**:
    If results aren't relevant, try:
    - More specific queries (add context/domain)
    - Different terminology (synonyms)
    - Breaking complex queries into simpler parts

## Tips

- Use **natural language** - the system uses semantic search, not keyword matching
- Be **specific** - "fix DSPy routing errors" is better than "errors"
- **Combine** with other commands: recall → apply solution → learn new variation
- Check **episodic memory** separately if you need conversation history

## Output Format

Results include:

- Matched text snippets
- Source file paths
- Relevance scores (0-1, higher = better match)
- Metadata (creation date, tags, etc.)
