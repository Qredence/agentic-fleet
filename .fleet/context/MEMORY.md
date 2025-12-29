# AgenticFleet Memory System

This directory contains the **Agentic Memory System** for this project. It is designed to help agents learn, remember, and improve over time while keeping your private data safe.

## Architecture

The system uses a **Two-Tier Memory** architecture:

1.  **Local Context (Tier 1)**: File-based, git-tracked templates but local content.
    - `core/`: Identity, project architecture, and user preferences.
    - `skills/`: "Handbooks" for specific tasks (e.g., debugging guides).
    - `recall/`: Session history and scratchpads.

2.  **Chroma Cloud (Tier 2)**: Private semantic search.
    - **Semantic Collection**: Facts about the project and user.
    - **Procedural Collection**: Embeddings of learned skills.
    - **Episodic Collection**: History of past sessions.

## Setup (First Run)

1.  **Install Dependencies**:
    The system uses a lightweight Python "engine" to talk to Chroma.

    ```bash
    uv pip install chromadb openai pyyaml
    ```

2.  **Configure Chroma**:
    Copy the template and add your API keys.

    ```bash
    cp .fleet/context/.chroma/config.template.yaml .fleet/context/.chroma/config.yaml
    ```

    Edit `.fleet/context/.chroma/config.yaml` with your Chroma Cloud credentials.

3.  **Initialize Memory**:
    Run the init skill (or script directly) to hydrate your local files from templates.
    ```bash
    uv run python .fleet/context/scripts/memory_manager.py init
    ```

## Usage

### For Agents

Agents are instructed to use this system via `AGENTS.md`.

- **Start**: Read `core/project.md` and `core/human.md`.
- **Search**: Use `/recall "query"` to find relevant skills or past solutions.
- **Learn**: Use `/learn` after solving a difficult problem to document the solution.

### For Humans

You can manually edit any file in `core/` or `skills/`.

- **`core/project.md`**: Update this when architecture changes.
- **`core/human.md`**: Update this with your preferences.
- **`skills/*.md`**: Write new guides manually if you prefer.

## Privacy & Git

- **Public Safe**: The _structure_ (scripts, templates, definitions) is committed to Git.
- **Private Safe**: Your _content_ (actual `.md` files in core/skills, and config) is ignored via `.gitignore`.
