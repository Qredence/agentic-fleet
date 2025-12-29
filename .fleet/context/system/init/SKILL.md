---
name: system-init
description: Initialize or hydrate the agent's memory system and verify configuration.
---

# System Initialization

This skill handles the initialization of the agent's memory system. It ensures that the necessary directory structures, configuration files, and core context templates are in place.

## Usage

Run this command at the start of a new project or when you need to reset/repair the memory system structure.

```bash
uv run python .fleet/context/scripts/memory_manager.py init
```

## Actions Performed

1.  **Hydrates Templates**: Copies `core/*.template.md` to active `core/*.md` files if they don't exist.
2.  **Config Setup**: Ensures `.chroma/config.yaml` exists (creating from template if needed).
3.  **Recall Scratchpad**: Creates `recall/current.md` for the current session context.

## Chroma Cloud Setup

After initialization, set up Chroma Cloud:

1.  **Edit config**: Add your Chroma Cloud credentials to `.fleet/context/.chroma/config.yaml`:

    ```yaml
    cloud:
      tenant: "your-tenant"
      database: "your-database"
      api_key: "your-api-key"
    ```

2.  **Create collections**: Run the setup command to create collections in Chroma Cloud:

    ```bash
    uv run python .fleet/context/scripts/memory_manager.py setup-chroma
    ```

3.  **Verify status**: Check that everything is connected:
    ```bash
    uv run python .fleet/context/scripts/memory_manager.py status
    ```

## Collections Created

| Collection   | Name                     | Purpose                      |
| ------------ | ------------------------ | ---------------------------- |
| `semantic`   | agentic-fleet-semantic   | Facts about project and user |
| `procedural` | agentic-fleet-procedural | Learned skills and patterns  |
| `episodic`   | agentic-fleet-episodic   | Session history and context  |

## Environment Variables (Optional)

Instead of config file, you can use environment variables:

- `CHROMA_API_KEY` - Your Chroma Cloud API key
- `CHROMA_TENANT` - Your tenant name
- `CHROMA_DATABASE` - Your database name
