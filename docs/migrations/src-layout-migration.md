# Src Layout Migration (October 12, 2025)

The AgenticFleet package moved from a flat module layout to the modern `src/` structure to improve import safety, align with PyPA guidance, and prepare the project for PyPI distribution as `agentic-fleet`.

## Objectives
- Adopt the `src/agenticfleet` package layout while keeping the import name `agenticfleet`.
- Publishable artifact renamed to `agentic-fleet` with a console entry point `agentic-fleet`.
- Protect existing workflows by updating imports, configuration loaders, and tests.

## Highlights

### Package structure before/after
```
# Before
AgenticFleet/
├── agents/
├── config/
├── workflows/
├── context_provider/
├── main.py
└── pyproject.toml

# After
AgenticFleet/
├── src/agenticfleet/
│   ├── agents/
│   ├── workflows/
│   ├── config/
│   ├── context/
│   ├── core/
│   └── cli/
├── tests/
├── docs/
└── pyproject.toml
```

### Key refactors
- All agent factories, workflow modules, configuration helpers, and context providers relocated under `src/agenticfleet/`.
- New `core/` package centralises exceptions, logging, and shared types.
- New `cli/` package hosts the REPL entry point used by the `agentic-fleet` console script.
- Existing scripts and tests updated to import from `agenticfleet.*` paths instead of top-level modules.

### Configuration updates
- `pyproject.toml` now targets `src/agenticfleet` for wheel builds and defines the console script entry point.
- UV dependency groups corrected to use `[dependency-groups]`, eliminating deprecation warnings.
- Agent configuration helpers resolve short identifiers (for example `"orchestrator"`) to the new `src/` locations.

## Validation
- `uv run pytest -v` → 28 tests passing (including 21 mem0 context provider cases).
- `uv run agentic-fleet` launches the CLI; `uv run python -m agenticfleet` remains supported.
- `uv run python test_config.py` confirms each agent factory, tool import, and workflow definition initialises successfully.

## Follow-on actions
- Keep agent temperature values in configuration for future runtime options (no longer passed to `ChatAgent` constructors).
- See `../operations/developer-environment.md` for the complementary UV tooling updates.
