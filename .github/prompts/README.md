# GitHub Copilot Prompts

This directory contains specialized prompts for GitHub Copilot to assist with project-specific tasks.

## Available Prompts

### 📝 create-agentsmd.prompt.md

**Purpose**: Generates a high-quality AGENTS.md file following the agents.md open format
**Usage**: Use when creating or updating the repository's AGENTS.md documentation
**Scope**: Generic prompt (not AgenticFleet-specific)

### 🔍 create-github-issues-for-unmet-specification-requirements.prompt.md

**Purpose**: Analyzes specifications and creates GitHub issues for unmet requirements
**Usage**: Use during feature planning or specification reviews
**Scope**: Project-specific for tracking implementation gaps

### 🧠 memory-merger.prompt.md

**Purpose**: Merges and consolidates memory/context information
**Usage**: Use when consolidating agent memory or context data
**Scope**: AgenticFleet-specific (relates to Mem0 context provider)

### 💾 remember.prompt.md

**Purpose**: Transforms lessons learned into domain-organized memory instructions
**Usage**: Use with `/remember` command to persist knowledge across sessions
**Syntax**: `/remember [>domain [scope]] lesson content`
**Scope**: Generic prompt for VS Code memory management

## How to Use

These prompts are automatically discovered by GitHub Copilot when working in this repository. They provide specialized context and instructions for specific tasks.

### Invoking Prompts

In GitHub Copilot Chat, you can reference these prompts by mentioning them or using relevant keywords that trigger their context.

### Prompt Organization

- **Generic prompts** (create-agentsmd, remember) - Reusable across projects
- **Project-specific prompts** (memory-merger, create-github-issues) - Tailored to AgenticFleet

## Best Practices

1. Keep prompts focused on a single, well-defined task
2. Include clear usage instructions in prompt metadata
3. Document prompt scope (generic vs project-specific)
4. Review and update prompts as project evolves

## Related Documentation

- [GitHub Copilot Instructions](../copilot-instructions.md) - Project-wide Copilot configuration
- [Microsoft Agent Framework Instructions](../instructions/microsoft-agent-framework-memory.instructions.md) - Agent framework patterns

---

**Note**: These prompts complement the main `.github/copilot-instructions.md` file, which provides overarching project context to Copilot.
