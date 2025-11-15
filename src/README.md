# DSPy-Enhanced Agent Framework

A powerful multi-agent workflow system combining Microsoft's agent-framework with DSPy's intelligent prompt optimization.

## Features

- 🧠 **Intelligent Task Routing**: DSPy-powered automatic task decomposition and agent selection
- 🔄 **Adaptive Workflows**: Self-improving workflows that learn from examples
- 👥 **Multi-Agent Orchestration**: Coordinate specialized agents efficiently
- 📊 **Real-time Monitoring**: Stream events for complete visibility
- 📝 **Comprehensive Logging**: Detailed 4-phase execution tracking with persistent history
- 📈 **Execution Analytics**: Built-in tools to analyze workflow performance
- 🔧 **Extensible Tools**: Code execution, web search, and custom tools
- 🛠️ **Tool-Aware DSPy**: DSPy modules understand and leverage tool capabilities for better routing
- 🤝 **Structured Agent Handoffs**: Optional handoff manager builds rich context packages between agents
- 📡 **Deep Observability**: OpenTelemetry tracing hooks into every workflow phase
- 🧬 **Reflective Prompt Evolution**: Optional dspy.GEPA optimizer to evolve routing prompts

See `CHANGELOG.md` for the latest release notes and migration tips.

## Installation

```bash
# Clone the repository
git clone https://github.com/qredence/agentic-fleet.git
cd agentic-fleet

# Create virtual environment
uv python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
uv pip install -e .
```

## Quick Start

### Using the Console Interface

The command-line interface for interacting with the framework:

```bash
# Basic usage
uv run python console.py run -m "Your question here"

# With verbose logging (see all DSPy decisions)
uv run python console.py run -m "Your question here" --verbose

# Save console output to file
uv run python console.py run -m "Your question here" --verbose 2>&1 | tee logs/console_output.log
```

### Programmatic Usage

```python
from agentic_fleet.workflows import create_supervisor_workflow
import asyncio

async def main():
    workflow = await create_supervisor_workflow()
    result = await workflow.run("Analyze the impact of AI on software development")
    print(result)

asyncio.run(main())
```

### Analyzing Execution History

View detailed statistics about past executions:

```bash
# Show overall summary and last 10 executions
uv run python scripts/analyze_history.py

# Show all statistics
uv run python scripts/analyze_history.py --all

# Show specific information
uv run python scripts/analyze_history.py --routing    # Routing mode distribution
uv run python scripts/analyze_history.py --agents     # Agent usage stats
uv run python scripts/analyze_history.py --timing     # Time breakdown by phase
```

### Self-Improvement from History

The framework can automatically learn from high-quality executions:

```bash
# Analyze execution history and add successful patterns as training examples
uv run python console.py self-improve

# Show statistics only (don't add examples yet)
uv run python console.py self-improve --stats-only

# Customize quality threshold
uv run python console.py self-improve --min-quality 9.0 --max-examples 10

# Or use the dedicated script
uv run python scripts/self_improve.py
uv run python scripts/self_improve.py --stats-only
```

**How it works:**

1. Analyzes execution history in `logs/execution_history.jsonl`
2. Identifies executions with quality score >= 8.0 (configurable)
3. Converts them to DSPy training examples
4. Adds to `data/supervisor_examples.json` (avoiding duplicates)
5. Clears compilation cache to force relearning
6. Next execution uses improved routing model

### Reflective Prompt Evolution with dspy.GEPA

Use GEPA to evolve the supervisor's routing prompts with textual feedback:

```bash
# Run GEPA with defaults from config/workflow_config.yaml
uv run python console.py gepa-optimize

# Example with custom options
uv run python console.py gepa-optimize \
  --examples data/supervisor_examples.json \
  --auto medium \
  --max-full-evals 80 \
  --use-history \
  --history-min-quality 9.0 \
  --history-limit 300 \
  --val-split 0.25
```

Enable GEPA by setting `dspy.optimization.use_gepa: true` in `config/workflow_config.yaml`. Additional fields let you control:

- `gepa_auto`, `gepa_max_full_evals`, `gepa_max_metric_calls`, `gepa_reflection_model`
- Training data: `examples_path`, optional history augmentation (`gepa_use_history_examples`, `gepa_history_min_quality`, `gepa_history_limit`)
- Validation behavior: `gepa_val_split`, `gepa_seed`
- Logging/output: `gepa_log_dir`, `gepa_perfect_score`

When enabled, workflow initialization automatically compiles the supervisor with GEPA and caches the optimized module in `logs/compiled_supervisor.pkl`.

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Documentation Index](export_dspy_framework/docs/INDEX.md)** - Start here for navigation
- **[Getting Started](export_dspy_framework/docs/users/getting-started.md)** - Installation and quick start
- **[User Guide](export_dspy_framework/docs/users/user-guide.md)** - Complete user documentation
- **[Configuration](export_dspy_framework/docs/users/configuration.md)** - Configuration guide
- **[Troubleshooting](export_dspy_framework/docs/users/troubleshooting.md)** - Common issues and solutions
- **[API Reference](export_dspy_framework/docs/developers/api-reference.md)** - Detailed API documentation
- **[Architecture](export_dspy_framework/docs/developers/architecture.md)** - System architecture and design
- **[Testing](export_dspy_framework/docs/developers/testing.md)** - Testing guide and best practices
- **[Contributing](export_dspy_framework/docs/developers/contributing.md)** - Development guidelines

### Feature Guides

- **[DSPy Optimizer Guide](export_dspy_framework/docs/guides/dspy-optimizer.md)** - BootstrapFewShot and GEPA optimizers
- **[Evaluation Guide](export_dspy_framework/docs/guides/evaluation.md)** - Evaluation framework and history-based evaluation
- **[Tracing Guide](export_dspy_framework/docs/guides/tracing.md)** - OpenTelemetry observability
- **[Logging and History](export_dspy_framework/docs/guides/logging-history.md)** - Logging system and execution history
- **[Quick Reference](export_dspy_framework/docs/guides/quick-reference.md)** - Quick command reference

## Configuration

1. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Then, add your API keys:

```env
OPENAI_API_KEY=your-key-here
TAVILY_API_KEY=your-tavily-key-here  # Get from https://tavily.com
```

**Note:** Tavily provides high-quality web search with citations. Sign up for a free API key at [tavily.com](https://tavily.com).

## Architecture

The system uses a hierarchical supervisor pattern with DSPy optimization:

- **Supervisor Agent**: Orchestrates workflow using DSPy routing
- **Specialist Agents**: Execute specific tasks (research, analysis, writing)
- **DSPy Module**: Optimizes prompts and learns from examples
- **Event System**: Provides real-time execution monitoring
- **Logging System**: Tracks all phases with persistent JSON history

### Workflow Execution Phases

Each workflow execution follows 4 phases:

1. **DSPy Task Analysis**: Analyzes task complexity, required capabilities, and tool requirements. Can optionally use tools (e.g., web search) to gather context.
2. **DSPy Task Routing**: Determines execution mode (sequential/parallel/delegated) and assigns agents based on task requirements and available tools
3. **Agent Execution**: Agents process the task according to routing decisions, using their assigned tools
4. **DSPy Quality Assessment**: Evaluates output quality and suggests improvements

All execution data is saved to `logs/execution_history.json` for later analysis.

### Structured Handoffs (Optional)

The `HandoffManager` can package context when one agent passes work to another:

1. Enable it after initialization:
   ```python
   workflow = SupervisorWorkflow()
   await workflow.initialize()
   workflow.enable_handoffs = True
   ```
2. The manager evaluates whether a handoff is warranted, captures the completed work, artifacts, success criteria, tool requirements, and quality checklist, then stores that context in `handoff_history`.
3. Sequential workflows automatically embed the latest handoff package in `current_execution` metadata so downstream agents can continue seamlessly.

Use `docs/guides/HISTORY_EVALUATION*.md` plus `tests/workflows/test_handoff_workflows.py` as living references for extending this subsystem (quality assessment hooks, analytics, etc.).

Toggle handoffs globally via `workflow.handoffs.enabled` in `config/workflow_config.yaml` or per-run with `console.py run --handoffs/--no-handoffs`.

### Tool-Aware DSPy Integration

The framework now includes **tool-aware DSPy** capabilities:

- **Tool Registry**: Centralized registry tracking all available tools, their capabilities, and which agents have access
- **Tool-Aware Routing**: DSPy routing decisions consider tool availability and requirements
- **Tool Usage Tracking**: Execution history includes tool usage statistics and patterns
- **Pre-Analysis Tool Usage**: DSPy can optionally use tools (like Tavily search) during task analysis to gather context

Tools like Tavily are automatically discovered and registered when agents are created. DSPy signatures have been enhanced to include tool information, enabling better routing decisions.

## Logging and History

The framework provides comprehensive logging at multiple levels:

- **Console Output**: Real-time rich UI showing agent progress
- **Workflow Logs**: Detailed timestamped logs in `logs/workflow.log`
- **Execution History**: Structured JSONL history in `logs/execution_history.jsonl` (preferred). Legacy JSON at `logs/execution_history.json` is still supported.

For complete documentation on logging features, see [docs/guides/LOGGING_AND_HISTORY.md](export_dspy_framework/docs/guides/LOGGING_AND_HISTORY.md).

## Tracing & Observability

The framework supports OpenTelemetry tracing through the **agent-framework**'s builtin instrumentation.
When enabled, spans are emitted for chat client calls, agent execution steps, workflow phases and (optionally) prompts & completions.

### Enable Tracing

1. Set tracing flags in `config/workflow_config.yaml`:

```yaml
tracing:
  enabled: true
  otlp_endpoint: http://localhost:4317 # Collector (AI Toolkit default)
  capture_sensitive: true # Prompts/completions; disable in production if needed
```

2. Or via environment variables (override config):

```env
TRACING_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
TRACING_SENSITIVE_DATA=true
```

3. Run any command (e.g. `python console.py run ...`). Tracing initializes early so that agent creation and DSPy compilation (GEPA) are captured.

### How It Works

`src/utils/tracing.py` calls `agent_framework.observability.setup_observability` if available; otherwise it falls back to a minimal OpenTelemetry OTLP exporter so you still get spans. Initialization is idempotent.

### Viewing Traces

Use the AI Toolkit tracing panel or any OTLP-compatible collector (Jaeger, Grafana Tempo, etc.). Set `OTEL_EXPORTER_OTLP_ENDPOINT` to your collector address if different from the default.

### Disabling Tracing

Set `TRACING_ENABLED=false` or `tracing.enabled: false` in YAML. No spans or overhead in that mode.

### Sensitive Data Guidance

Leave `capture_sensitive: false` (or `TRACING_SENSITIVE_DATA=false`) in shared/staging/production environments to avoid exporting raw prompts/responses.

See full guide: [docs/guides/TRACING.md](export_dspy_framework/docs/guides/TRACING.md)

## Evaluation Framework

Batch evaluate workflow behavior against a dataset of tasks with configurable metrics.

### Metrics Implemented

Default metrics (configurable via `evaluation.metrics`):
| Metric | Description |
|--------|-------------|
| `quality_score` | Uses internal quality assessment score (0-10) |
| `keyword_success` | 1/0 if all specified task keywords appear in output |
| `latency_seconds` | Total execution time per task |
| `routing_efficiency` | Unique agents used / assigned (proxy for efficiency) |
| `refinement_triggered` | 1 if refinement suggestions present, else 0 |

### Quick Start

1. Enable in `config/workflow_config.yaml`:

```yaml
evaluation:
  enabled: true
```

2. Add or edit dataset at `data/evaluation_tasks.jsonl` (each line JSON with at least `message`; optional `keywords`).
3. Run:

```bash
uv run python console.py evaluate --max-tasks 3
```

Outputs:

- `logs/evaluation/evaluation_report.jsonl` – per-task metrics
- `logs/evaluation/evaluation_summary.json` – aggregate stats

### Customizing

Override metrics at runtime:

```bash
uv run python console.py evaluate --metrics quality_score,latency_seconds
```

See full guide: [docs/guides/evaluation.md](export_dspy_framework/docs/guides/evaluation.md).

## Examples

See the `examples/` directory for complete working examples.

## License

MIT License - See LICENSE file for details.

## Author

Created by Zochory - 2025-11-03
