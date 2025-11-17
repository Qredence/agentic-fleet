# Configuration Guide

## Overview

The DSPy-Enhanced Agent Framework uses a hierarchical configuration system that combines:

- YAML configuration files (`config/workflow_config.yaml`)
- Environment variables (`.env`)
- Programmatic configuration (Python code)

Configuration is validated using Pydantic schemas to ensure type safety and catch errors early.

## Configuration Hierarchy

Configuration values are resolved in this order (highest priority first):

1. **Programmatic configuration** (passed to WorkflowConfig)
2. **Environment variables**
3. **YAML configuration file**
4. **Default values** (in code)

## Configuration File Structure

### Complete Example

```yaml
# config/workflow_config.yaml

# DSPy Configuration
dspy:
  model: gpt-5-mini # Model for DSPy supervisor
  temperature: 0.7 # 0.0-2.0, controls randomness
  max_tokens: 2000 # Max tokens per DSPy call

  optimization:
    enabled: true # Enable DSPy compilation
    examples_path: data/supervisor_examples.json
    metric_threshold: 0.8 # Minimum routing accuracy
    max_bootstrapped_demos: 4 # Few-shot examples per prompt
    use_gepa: false # Switch to dspy.GEPA optimizer
    gepa_auto: light # light|medium|heavy search budget
    gepa_max_full_evals: 50
    gepa_max_metric_calls: 150
    gepa_reflection_model:
    gepa_log_dir: logs/gepa
    gepa_perfect_score: 1.0
    gepa_use_history_examples: false
    gepa_history_min_quality: 8.0
    gepa_history_limit: 200
    gepa_val_split: 0.2
    gepa_seed: 13

# Workflow Configuration
workflow:
  supervisor:
    max_rounds: 15 # Max agent conversation turns
    max_stalls: 3 # Max stuck iterations before reset
    max_resets: 2 # Max workflow resets
    enable_streaming: true # Stream events for live UI

  execution:
    parallel_threshold: 3 # Min agents for parallel mode
    timeout_seconds: 300 # Max execution time
    retry_attempts: 2 # Retry failed operations

  quality:
    refinement_threshold: 8.0 # Quality score threshold
    enable_refinement: true # Auto-refine low-quality results

# Agent Configuration
agents:
  researcher:
    model: gpt-4.1 # Agent-specific model
    tools:
      - TavilySearchTool
    temperature: 0.5 # Lower = more factual

  analyst:
    model: gpt-4.1
    tools:
      - HostedCodeInterpreterTool
    temperature: 0.3 # Very low for precision

  writer:
    model: gpt-4.1
    tools: []
    temperature: 0.7 # Higher for creativity

  reviewer:
    model: gpt-4.1
    tools: []
    temperature: 0.2 # Low for consistency

# Tool Configuration
tools:
  enable_tool_aware_routing: true # DSPy considers tools
  pre_analysis_tool_usage: true # Use tools in analysis
  tool_registry_cache: true # Cache tool metadata
  tool_usage_tracking: true # Track tool usage

# Logging Configuration
logging:
  level: INFO # DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: logs/workflow.log # Log file path
  save_history: true # Save execution history
  history_file: logs/execution_history.jsonl
  verbose: true # Verbose execution logs

# OpenAI Configuration
openai:
  enable_completion_storage: false # Store completions in OpenAI
```

## Command-Line Overrides

Many configuration values can be overridden at runtime without editing `workflow_config.yaml`. The CLI flags map directly onto config keys for quick experimentation:

```bash
# Swap the DSPy model for a single run
uv run agentic-fleet run -m "task" --model gpt-3.5-turbo

# Skip compilation when iterating quickly
uv run agentic-fleet run -m "task" --no-compile

# Turn on verbose logging/streaming
uv run agentic-fleet run -m "task" --verbose
```

Use `uv run agentic-fleet run --help` to inspect the full list of override flags.

## Configuration Sections

### DSPy Configuration

Controls DSPy supervisor behavior and optimization.

**model** (`str`, default: `"gpt-4.1"`)

- Language model for DSPy routing decisions
- Options: `"gpt-5-mini"`, `"gpt-4.1"`, `"gpt-4o"`
- Recommendation: Use `"gpt-5-mini"` for development, `"gpt-4.1"` for production

**temperature** (`float`, default: `0.7`, range: `0.0-2.0`)

- Controls randomness in DSPy decisions
- Lower = more consistent routing
- Higher = more creative routing

**optimization.enabled** (`bool`, default: `true`)

- Enable DSPy compilation with training examples
- First run is slower (compilation time)
- Subsequent runs are faster (cached)

**optimization.examples_path** (`str`, default: `"data/supervisor_examples.json"`)

- Path to training examples for DSPy
- See [Training Examples](#training-examples) section

**optimization.metric_threshold** (`float`, default: `0.8`, range: `0.0-1.0`)

- Minimum routing accuracy during compilation
- Higher = stricter optimization

**optimization.max_bootstrapped_demos** (`int`, default: `4`, range: `1-20`)

- Number of few-shot examples per DSPy prompt
- More = better routing but slower and more expensive
- Recommendation: 4-8 for most use cases

**GEPA-specific options**

- `optimization.use_gepa` (`bool`, default: `false`): switch from BootstrapFewShot to dspy.GEPA.
- `optimization.gepa_auto` (`"light"|"medium"|"heavy"`, default: `light`): controls amount of exploration per iteration.
- `optimization.gepa_max_full_evals` (`int`, default: `50`): cap on full GEPA evaluations.
- `optimization.gepa_max_metric_calls` (`int`, default: `150`): guardrail for expensive feedback metrics.
- `optimization.gepa_reflection_model` (`str|None`): optional LM ID dedicated to reflective feedback (defaults to `dspy.model`).
- `optimization.gepa_log_dir` (`str`, default: `logs/gepa`): directory for GEPA traces/stats.
- `optimization.gepa_perfect_score` (`float`, default: `1.0`): max score reported by the metric.
- `optimization.gepa_use_history_examples` (`bool`, default: `false`): merge high-quality executions from `logs/execution_history.*` into the training set.
- `optimization.gepa_history_min_quality` (`float`, default: `8.0`): minimum quality score for harvested executions.
- `optimization.gepa_history_limit` (`int`, default: `200`): lookback window when harvesting history.
- `optimization.gepa_val_split` (`float`, default: `0.2`): fraction of routing examples held out for validation.
- `optimization.gepa_seed` (`int`, default: `13`): RNG seed for deterministic shuffles.

### Workflow Configuration

Controls overall workflow behavior.

**supervisor.max_rounds** (`int`, default: `15`, range: `1-100`)

- Maximum agent conversation turns
- Prevents infinite loops

**supervisor.max_stalls** (`int`, default: `3`, range: `1-20`)

- Maximum iterations without progress
- Triggers reset or termination

**supervisor.max_resets** (`int`, default: `2`, range: `0-10`)

- Maximum workflow resets
- After this, workflow terminates

**supervisor.enable_streaming** (`bool`, default: `true`)

- Enable event streaming
- Optional, enables real-time event streaming

**execution.parallel_threshold** (`int`, default: `3`, min: `1`)

- Minimum subtasks to trigger parallel mode
- Lower = more parallel execution

**execution.timeout_seconds** (`int`, default: `300`, min: `1`)

- Maximum execution time per task
- Prevents hanging operations

**execution.retry_attempts** (`int`, default: `2`, min: `0`)

- Number of retry attempts for failed operations

**quality.refinement_threshold** (`float`, default: `8.0`, range: `0.0-10.0`)

- Quality score below which results are refined
- Lower = more refinement

**quality.enable_refinement** (`bool`, default: `true`)

- Enable automatic refinement of low-quality results

### Agent Configuration

Per-agent settings override defaults.

**model** (`str`, default: `"gpt-4.1"`)

- Language model for this specific agent
- Overrides `dspy.model` default

**tools** (`List[str]`, default: `[]`)

- List of tool names available to agent
- Built-in: `TavilySearchTool`, `HostedCodeInterpreterTool`

**temperature** (`float`, default: `0.7`, range: `0.0-2.0`)

- Agent-specific temperature
- Recommendations:
  - Researcher: 0.5 (balanced)
  - Analyst: 0.3 (precise)
  - Writer: 0.7 (creative)
  - Reviewer: 0.2 (consistent)

### Tool Configuration

Controls tool-aware features and intelligent routing based on tool availability.

**enable_tool_aware_routing** (`bool`, default: `true`)

- DSPy considers tool availability when routing
- Disable if tools should not influence routing

**pre_analysis_tool_usage** (`bool`, default: `true`)

- Allow DSPy to use tools during task analysis
- Enables web search for context gathering

**tool_registry_cache** (`bool`, default: `true`)

- Cache tool metadata for performance

**tool_usage_tracking** (`bool`, default: `true`)

- Track which tools are used in execution history

### How Tool Awareness Works

The framework includes a centralized **ToolRegistry** that tracks all available tools, their capabilities, and which agents have access to them. This enables DSPy modules to make intelligent routing decisions based on tool availability.

**Automatic Tool Discovery**:

- During initialization, the workflow scans each agent's `chat_options.tools` list
- Tools are registered with metadata: name, description, capabilities, use cases, and aliases
- The registry infers capabilities from tool names and descriptions (e.g., "search" → web_search capability)

**DSPy Integration**:

- Tool descriptions are injected into DSPy signatures (`ToolAwareTaskAnalysis`, `TaskRouting`)
- The supervisor's instructions include a live tool catalog for model context
- DSPy's `forward()` method prefers tool-aware analysis when tools are available
- Routing decisions now include `tool_requirements` field listing needed tools

**Tool Visibility in Prompts**:

```
Available tools:
- tavily_search | aliases: TavilySearchTool (available to Researcher): Search the web for real-time information using Tavily. Provides accurate, up-to-date results with source citations. [Capabilities: citations, real_time, web_access, web_search] Use cases: Finding up-to-date information, Researching current events, Gathering facts with citations
- HostedCodeInterpreterTool | aliases: HostedCodeInterpreterAdapter (available to Analyst): Execute Python code snippets in an isolated sandbox environment for analysis, data transformation, and quick computation. [Capabilities: code_execution] Use cases: Data analysis and computation, Running Python code, Creating visualizations
```

**Example Tool-Aware Routing**:

```python
# Task requiring web search → automatically routed to Researcher
await workflow.run("What are the latest AI breakthroughs this week?")
# DSPy sees: TavilySearchTool available to Researcher, routes accordingly

# Task requiring computation → automatically routed to Analyst
await workflow.run("Calculate compound interest for $10,000 at 5% over 10 years")
# DSPy sees: HostedCodeInterpreterTool available to Analyst, routes accordingly
```

**Aliasing Strategy**:

- Tools often have both a runtime name (e.g., `tavily_search`) and a class name (e.g., `TavilySearchTool`)
- The registry automatically creates aliases to support both naming conventions
- This prevents external parsing errors and improves tool recognition

**Multi-Tool Support**:

- The registry now supports agents with multiple tools (list/tuple of tools)
- Future agents can have access to multiple capabilities without code changes

**Disabling Tool Awareness**:

```yaml
tools:
  enable_tool_aware_routing: false # DSPy ignores tools when routing
  pre_analysis_tool_usage: false # DSPy doesn't use tools during analysis
```

### Logging Configuration

Controls logging behavior.

**level** (`str`, default: `"INFO"`)

- Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**format** (`str`)

- Log format string (Python logging format)

**file** (`str`, default: `"logs/workflow.log"`)

- Path to log file

**save_history** (`bool`, default: `true`)

- Save execution history

**history_file** (`str`, default: `"logs/execution_history.jsonl"`)

- Path to history file
- Use `.jsonl` for performance, `.json` for readability

**verbose** (`bool`, default: `true`)

- Enable verbose execution logs

### Tracing Configuration

Controls OpenTelemetry observability.

```yaml
tracing:
  enabled: true
  otlp_endpoint: http://localhost:4317
  capture_sensitive: true
```

- **enabled** (`bool`, default: `false`): When `true`, `initialize_tracing()` configures either `agent_framework.observability` or the built-in fallback exporter.
- **otlp_endpoint** (`str`, default: `http://localhost:4317`): OTLP/gRPC collector endpoint (Jaeger/AI Toolkit/OTel collector). Port 4317 is for OTLP/gRPC, 4318 for OTLP/HTTP. Port 16686 is Jaeger UI only. Can be overridden via `OTEL_EXPORTER_OTLP_ENDPOINT`.
- **capture_sensitive** (`bool`, default: `true`): Whether to export prompts + completions. Override with `TRACING_SENSITIVE_DATA`.

Environment overrides:

```env
TRACING_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
TRACING_SENSITIVE_DATA=false
```

### Evaluation Configuration

Batch evaluation lives under the `evaluation` section:

```yaml
evaluation:
  enabled: true
  dataset_path: data/evaluation_tasks.jsonl
  output_dir: logs/evaluation
  metrics:
    - quality_score
    - keyword_success
  max_tasks: 0
  stop_on_failure: false
```

- **enabled** (`bool`, default: `false`): Toggle evaluation CLI (for example, via `agentic-fleet evaluate`) and guards inside `Evaluator`.
- **dataset_path** (`str`): JSONL dataset containing tasks/keywords.
- **output_dir** (`str`): Where summaries + per-task metrics are written.
- **metrics** (`List[str]`): Metric IDs from `src/evaluation/metrics.py`.
- **max_tasks** (`int`, default: `0` = no cap): Useful for spot checks.
- **stop_on_failure** (`bool`): Abort as soon as a success metric fails.

Pair this config with the helpers in `scripts/create_history_evaluation.py` for regenerating datasets from execution history.

### Handoff Configuration

Located under `workflow.handoffs`.

```yaml
workflow:
  handoffs:
    enabled: true
```

- **enabled** (`bool`, default: `true`): Turns structured handoffs on/off. When disabled, sequential execution reverts to simple pass-through and DSPy routing ignores handoff history. Override per-run with `agentic-fleet run --handoffs/--no-handoffs`.

## Environment Variables

### Required

**OPENAI_API_KEY**

- OpenAI API key for language models
- Get from: https://platform.openai.com/api-keys

### Optional

**TAVILY_API_KEY**

- Tavily API key for web search
- Get from: https://tavily.com
- Highly recommended for research tasks

**OPENAI_BASE_URL**

- Custom OpenAI endpoint
- Use for Azure OpenAI or custom deployments
- Example: `https://your-resource.openai.azure.com/`

## Training Examples

Training examples teach DSPy optimal routing patterns. Format:

```json
{
  "task": "Research and analyze the impact of AI on healthcare",
  "team": "Researcher: Web research specialist\nAnalyst: Data analysis expert",
  "available_tools": "- TavilySearchTool (available to Researcher): ...",
  "context": "Initial research task",
  "assigned_to": "Researcher,Analyst",
  "mode": "sequential",
  "tool_requirements": ["TavilySearchTool"]
}
```

**Fields**:

- `task`: Example task (what user might ask)
- `team`: Available agents and descriptions
- `available_tools`: Tool descriptions
- `context`: Additional context
- `assigned_to`: Correct agents to use (comma-separated)
- `mode`: Correct execution mode
- `tool_requirements`: Tools needed

**Best Practices**:

- Include 20-50 examples for robust routing
- Cover all execution modes
- Include tool-using and non-tool examples
- Add edge cases and boundary conditions
- Test after adding examples: `agentic-fleet run -m "Test task" --verbose`

## Programmatic Configuration

Override configuration in code:

```python
from src.workflows.supervisor_workflow import WorkflowConfig, SupervisorWorkflow

# Create custom config
config = WorkflowConfig(
    dspy_model="gpt-5-mini",
    refinement_threshold=9.0,
    enable_refinement=True,
    max_rounds=20,
    agent_models={
        "researcher": "gpt-4.1",
        "analyst": "gpt-4.1",
        "writer": "gpt-5-mini",
        "reviewer": "gpt-5-mini",
    },
    agent_temperatures={
        "researcher": 0.4,
        "analyst": 0.2,
        "writer": 0.8,
        "reviewer": 0.1,
    },
)

# Use custom config
workflow = SupervisorWorkflow(config=config)
await workflow.initialize()
```

## Performance Tuning

### Faster Startup

```yaml
dspy:
  optimization:
    enabled: true # Skip compilation (or use --no-compile flag)
```

### Better Routing Accuracy

```yaml
dspy:
  model: gpt-5-mini # Use smarter model
  optimization:
    max_bootstrapped_demos: 8 # More examples per prompt
```

Add more training examples to `data/supervisor_examples.json`.

### Lower Costs

```yaml
dspy:
  model: gpt-5-mini # Cheaper model

agents:
  writer:
    model: gpt-5-mini # Use cheaper models for less critical agents
  reviewer:
    model: gpt-5-mini
```

### Faster History

```yaml
logging:
  history_file: logs/execution_history.jsonl # JSONL is 10-100x faster
```

## Configuration Validation

The framework validates configuration at startup using Pydantic schemas:

```python
from src.utils.config_schema import validate_config
from src.workflows.exceptions import ConfigurationError

try:
    schema = validate_config(config_dict)
    print("✓ Configuration is valid")
except ConfigurationError as e:
    print(f"✗ Invalid configuration: {e}")
    if e.config_key:
        print(f"  Problem with key: {e.config_key}")
```

### Validation Rules

- `temperature`: Must be 0.0-2.0
- `refinement_threshold`: Must be 0.0-10.0
- `max_rounds`: Must be 1-100
- `max_stalls`: Must be 1-20
- `logging.level`: Must be valid Python logging level
- `history_file`: Must have `.json` or `.jsonl` extension

## Migration from Older Versions

### Breaking Changes

1. **History format**: Execution history now appends to `logs/execution_history.jsonl`. The legacy `.json` file is still readable, but all tooling writes JSONL for better streaming performance.
2. **WorkflowConfig fields**: New required attributes (quality thresholds, streaming flags, tool switches) were added in v0.5. If you instantiate `WorkflowConfig` manually, supply the new fields or rely on defaults.
3. **Optional `TAVILY_API_KEY`**: Web search is now optional. When the key is missing, the Researcher agent automatically degrades to non-search mode. Run `uv run python console.py list_agents` to confirm the active capabilities.

### JSON to JSONL History

```python
from src.utils.history_manager import HistoryManager

# Load from old JSON format
old_manager = HistoryManager(history_format="json")
executions = old_manager.load_history()

# Save to new JSONL format
new_manager = HistoryManager(history_format="jsonl")
for execution in executions:
    new_manager.save_execution(execution)
```

### Update Configuration

If upgrading from older version:

1. Add new sections to `workflow_config.yaml`:

```yaml
tools:
  enable_tool_aware_routing: true
  pre_analysis_tool_usage: true

quality:
  refinement_threshold: 8.0
  enable_refinement: true
```

2. Update history file path:

```yaml
logging:
  history_file: logs/execution_history.jsonl # Changed from .json
```

### New in v0.5

- **Cached compilation**: Compiled DSPy supervisors are cached under `logs/compiled_supervisor.pkl`, shrinking cold-start time by ~5–10 seconds.
- **Parallel execution resilience**: Failures inside one parallel branch no longer terminate the entire workflow; the supervisor retries or continues with remaining agents.
- **Configurable refinement**: `workflow.quality.refinement_threshold` and `workflow.quality.enable_refinement` tune when the Reviewer requests another pass.
- **Completion storage controls**: `openai.enable_completion_storage` lets you disable OpenAI's default query storage for privacy-sensitive runs.
- **Tool-aware routing**: Centralized registry plus DSPy signature updates surface tool metadata inside prompts (`tools.*` section).
- **Tracing controls**: `tracing.enabled`, `tracing.otlp_endpoint`, and env overrides make observability opt-in per environment.
- **Evaluation suite**: `evaluation.*` keys wire up dataset paths, metrics, and CLI defaults for batch assessments.
- **Structured handoffs**: `SupervisorWorkflow.enable_handoffs` unlocks rich agent-to-agent context passing (see `src/workflows/handoff_manager.py`).

## Cache Management

Use the `manage_cache.py` helper to inspect or reset the DSPy compilation cache:

```bash
# Show the current cache metadata (path, size, age)
uv run python manage_cache.py --info

# Clear the compiled supervisor cache to force recompilation
uv run python manage_cache.py --clear
```

Clearing the cache is recommended whenever you update `data/supervisor_examples.json` or switch models.

## Examples

### Minimal Configuration

```yaml
dspy:
  model: gpt-5-mini
  optimization:
    enabled: true

workflow:
  supervisor:
    enable_streaming: true

logging:
  history_file: logs/execution_history.jsonl
```

### Production Configuration

```yaml
dspy:
  model: gpt-4.1
  temperature: 0.6
  optimization:
    enabled: true
    max_bootstrapped_demos: 8

workflow:
  supervisor:
    max_rounds: 20
    max_stalls: 5

  quality:
    refinement_threshold: 9.0 # Stricter quality
    enable_refinement: true

agents:
  researcher:
    model: gpt-4.1
    temperature: 0.4
  analyst:
    model: gpt-4.1
    temperature: 0.2
  writer:
    model: gpt-4.1
    temperature: 0.7
  reviewer:
    model: gpt-4.1
    temperature: 0.1

tools:
  enable_tool_aware_routing: true
  pre_analysis_tool_usage: true
  tool_usage_tracking: true

logging:
  level: INFO
  history_file: logs/execution_history.jsonl
  verbose: true
```

### Development Configuration

```yaml
dspy:
  model: gpt-5-mini # Cheaper for testing
  optimization:
    enabled: false # Skip compilation for speed

workflow:
  supervisor:
    max_rounds: 10

  quality:
    refinement_threshold: 7.0 # More lenient
    enable_refinement: false # Disable for speed

logging:
  level: DEBUG # More detailed logs
  verbose: true
```

## Troubleshooting

### "TAVILY_API_KEY not set" warning

- **Impact**: The Researcher agent runs without web search and may return partial answers.
- **Fix**: Add `TAVILY_API_KEY` to `.env` or accept the degraded mode; the workflow auto-detects the key at startup.

### Config file not loading

- Ensure `config/workflow_config.yaml` exists and contains valid YAML (use `uv run python -m yaml lint` if unsure).
- When the file is missing, defaults kick in—check the active config by running `uv run agentic-fleet run --show-config`.

### Cached module feels stale

- Run `uv run python manage_cache.py --clear` after updating `data/supervisor_examples.json` or switching models.
- Verify cache health with `uv run python manage_cache.py --info`; stale timestamps usually indicate a restart is needed.

## Operational Best Practices

- Start with the defaults; the shipped configuration balances speed, quality, and cost for most users.
- Disable completion storage (`openai.enable_completion_storage: false`) for privacy-sensitive deployments.
- Prefer JSONL history for append-only persistence and faster analytics.
- Keep the compiled supervisor cache warm to avoid repeated DSPy compilations in production.
- Monitor Tavily usage and only provision the API key when web search is required.
