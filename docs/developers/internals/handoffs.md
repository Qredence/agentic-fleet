# Handoff Workflows Quick Start Guide

**Quick reference for implementing intelligent agent handoffs with DSPy**

---

## Overview

Agent handoffs enable seamless work transitions between specialized agents with:

- 🎯 **DSPy-powered decisions**: Intelligent handoff evaluation
- 📦 **Rich context passing**: Structured metadata and artifacts
- 📊 **Quality tracking**: Monitor handoff success rates
- 🔄 **Adaptive execution**: Dynamic workflow adjustments

---

## Quick Example

### Basic Handoff

```python
from agentic_fleet.workflows.handoff import HandoffManager

# Initialize
handoff_manager = HandoffManager(dspy_supervisor)

# Evaluate if handoff is needed
next_agent = await handoff_manager.evaluate_handoff(
    current_agent="Researcher",
    work_completed="Found 10 relevant articles on AI trends",
    remaining_work="Need to analyze data and create visualizations",
    available_agents={
        "Analyst": "Data analysis and visualization expert",
        "Writer": "Content creation specialist"
    }
)

# Result: "Analyst" (DSPy recommends data expert)

# Create handoff package
handoff = await handoff_manager.create_handoff_package(
    from_agent="Researcher",
    to_agent="Analyst",
    work_completed="Research findings...",
    artifacts={"articles": [...], "data": {...}},
    remaining_objectives=["Analyze trends", "Create charts"]
)

# Handoff package includes:
# - Structured context
# - Quality checklist
# - Tool requirements
# - Success criteria
```

### Configuration

```yaml
# config/workflow_config.yaml
workflow:
  handoff:
    enabled: true
    evaluation_threshold: 0.7
    enable_handoffs: true # Enable structured handoffs
    track_artifacts: true
```

---

## Key Concepts

### 1. HandoffContext

Structured package passed between agents:

```python
@dataclass
class HandoffContext:
    from_agent: str              # Who is handing off
    to_agent: str                # Who receives
    work_completed: str          # What's done
    artifacts: Dict[str, Any]    # Data, files, results
    remaining_objectives: List   # What's next
    success_criteria: List       # How to measure success
    tool_requirements: List      # Tools needed
    quality_checklist: List      # Quality gates
```

### 2. DSPy Signatures for Handoffs

**HandoffDecision** - Determine if handoff is needed:

```python
Input:  current_agent, work_completed, remaining_work, available_agents
Output: should_handoff (yes/no), next_agent, handoff_reason
```

**HandoffProtocol** - Structure the handoff:

```python
Input:  from_agent, to_agent, work_completed, artifacts, objectives
Output: handoff_package, quality_checklist, estimated_effort
```

**CapabilityMatching** - Find best agent:

```python
Input:  task_requirements, agent_capabilities, tool_availability
Output: best_match, capability_gaps, confidence_score
```

### 3. Execution Modes

**Sequential with Handoffs** (Enhanced):

```
Researcher → [Handoff Package] → Analyst → [Handoff Package] → Writer
```

**Adaptive Mode** (NEW):

```
Start Sequential → Evaluate Progress → Switch to Parallel if needed
```

---

## Implementation Checklist

### Phase 1: Basic Handoffs (Week 1-2)

- [ ] Add `handoff_signatures.py` with DSPy signatures
- [ ] Implement `HandoffManager` class
- [ ] Update `SupervisorWorkflow` to use handoffs
- [ ] Add handoff tracking to execution history
- [ ] Write tests for handoff scenarios

### Phase 2: Enhanced DSPy (Week 3-4)

- [ ] Enhance `TaskRouting` with handoff strategy
- [ ] Add `CapabilityMatching` module
- [ ] Update progress evaluation with handoff awareness
- [ ] Add confidence scoring

### Phase 3: Advanced GEPA (Week 5-6)

- [ ] Implement enhanced feedback metric
- [ ] Add handoff quality evaluation
- [ ] Enable multi-objective optimization
- [ ] Set up continuous learning

### Phase 4: Adaptive Execution (Week 7-8)

- [ ] Implement adaptive execution mode
- [ ] Add dynamic mode switching
- [ ] Create monitoring dashboard

---

## Usage Patterns

### Pattern 1: Research → Analysis → Writing

```python
async def research_analysis_writing_workflow(task: str):
    workflow = SupervisorWorkflowWithHandoffs(config)

    # DSPy will automatically:
    # 1. Route to Researcher first
    # 2. Evaluate handoff after research
    # 3. Create handoff package for Analyst
    # 4. Handoff from Analyst to Writer
    # 5. Track all handoffs in history

    result = await workflow.run(task)

    # Check handoff statistics
    stats = workflow.handoff_manager.get_handoff_summary()
    print(f"Total handoffs: {stats['total_handoffs']}")
    print(f"Success rate: {stats['success_rate']}")
```

### Pattern 2: Capability-Based Routing

```python
# Automatically find best agent for task
capability_matcher = dspy.ChainOfThought(CapabilityMatching)

match = capability_matcher(
    task_requirements="Analyze financial data and create projections",
    agent_capabilities=get_all_agent_capabilities(),
    tool_availability=tool_registry.get_tool_descriptions()
)

print(f"Best match: {match.best_match}")
print(f"Confidence: {match.confidence}/10")

if float(match.confidence) < 7.0:
    # Low confidence, check alternatives
    print(f"Fallbacks: {match.fallback_agents}")
```

### Pattern 3: Adaptive Execution

```python
# Start with one mode, adapt based on progress
config = WorkflowConfig(
    execution_mode="adaptive",
    adaptation_threshold=0.6
)

workflow = SupervisorWorkflowWithHandoffs(config)

# Workflow will:
# - Start sequential
# - Monitor progress
# - Switch to parallel if blocked
# - Adjust based on agent performance
result = await workflow.run(complex_task)
```

---

## GEPA Training for Handoffs

### Preparing Training Examples

```json
{
  "task": "Research market trends and create analysis report",
  "team": "Researcher: Web search expert\nAnalyst: Data analysis\nWriter: Content",
  "available_tools": "TavilySearchTool, HostedCodeInterpreterTool",
  "assigned_to": "Researcher,Analyst,Writer",
  "mode": "sequential",
  "tool_requirements": ["TavilySearchTool", "HostedCodeInterpreterTool"],

  "_comment": "NEW handoff fields",
  "handoff_strategy": "Research data → Analyst processes → Writer summarizes",
  "handoff_points": ["After data collection", "After analysis"],
  "quality_gates": [
    "Verify data quality",
    "Validate analysis",
    "Review writing"
  ]
}
```

### Enhanced GEPA Metric

```python
from src.agentic_fleet.utils.gepa_optimizer import build_advanced_routing_feedback_metric

# Create metric with handoff evaluation
metric = build_advanced_routing_feedback_metric(
    perfect_score=1.0,
    enable_adaptive_weights=True,    # Weights adjust per task
    track_handoff_quality=True       # Evaluate handoff decisions
)

# Score breakdown:
# - Agent assignment: 35%
# - Execution mode: 25%
# - Tool selection: 15%
# - Handoff strategy: 15%  (NEW)
# - Subtask quality: 10%   (NEW)

# Compile with GEPA
compiled = optimize_with_gepa(
    module=supervisor,
    trainset=trainset,
    valset=valset,
    metric=metric,
    auto="medium",
    max_full_evals=100
)
```

---

## Monitoring & Debugging

### View Handoff History

```python
# Get handoff statistics
stats = workflow.handoff_manager.get_handoff_summary()

print(f"""
Handoff Statistics:
- Total handoffs: {stats['total_handoffs']}
- Most common: {stats['most_common_handoffs']}
- Average per task: {stats['avg_handoffs_per_task']:.1f}
"""
)

# View specific handoff
for handoff in workflow.handoff_manager.handoff_history:
    print(f"{handoff.from_agent} → {handoff.to_agent}")
    print(f"  Effort: {handoff.estimated_effort}")
    print(f"  Objectives: {len(handoff.remaining_objectives)}")
```

### Execution History

```python
from src.agentic_fleet.utils.history_manager import HistoryManager

history = HistoryManager()
executions = history.load_history(limit=10)

for ex in executions:
    if 'handoff_history' in ex:
        print(f"Task: {ex['task'][:50]}")
        print(f"Handoffs: {len(ex['handoff_history'])}")
        print(f"Quality: {ex['quality']['score']}/10")
        print()
```

### Analyze Handoff Effectiveness

```python
# Check if handoffs improve quality
handoff_tasks = [ex for ex in executions if ex.get('handoff_history')]
no_handoff_tasks = [ex for ex in executions if not ex.get('handoff_history')]

avg_with_handoffs = np.mean([ex['quality']['score'] for ex in handoff_tasks])
avg_without = np.mean([ex['quality']['score'] for ex in no_handoff_tasks])

print(f"Avg quality with handoffs: {avg_with_handoffs:.1f}/10")
print(f"Avg quality without: {avg_without:.1f}/10")
print(f"Improvement: {avg_with_handoffs - avg_without:+.1f} points")
```

---

## Performance Considerations

### Handoff Overhead

**Estimated overhead per handoff:**

- DSPy evaluation: ~0.5-1.0s
- Package creation: ~0.2-0.5s
- Context formatting: ~0.1s
- **Total: ~0.8-1.6s per handoff**

**Optimization strategies:**

1. **Cache handoff decisions** for similar patterns
2. **Parallel evaluation** during agent execution
3. **Threshold tuning** to reduce unnecessary handoffs
4. **Batch processing** for multi-handoff workflows

### When to Use Handoffs

✅ **Use handoffs when:**

- Sequential work requires specialized agents
- Context needs to be preserved between stages
- Quality gates between steps are important
- Agent capabilities vary significantly

❌ **Skip handoffs when:**

- Single agent can complete task
- Task is simple/straightforward
- Handoff overhead > task complexity
- Parallel execution is more efficient

---

## Troubleshooting

### Common Issues

**1. Too many handoffs**

```python
# Symptom: Agents ping-pong work back and forth
# Solution: Adjust handoff evaluation logic or disable handoffs for simple tasks
config = WorkflowConfig(enable_handoffs=False)

# Or modify handoff evaluation threshold in HandoffManager
# (requires code changes to HandoffManager.evaluate_handoff method)
```

**2. Poor handoff quality**

```python
# Symptom: Next agent can't use handoff context
# Solution: Enhance handoff package formatting

def _format_handoff_input(self, handoff: HandoffContext) -> str:
    # Add more structure
    # Include examples
    # Provide clear instructions
    return formatted_input
```

**3. Wrong agent selection**

```python
# Symptom: Capability matcher selects suboptimal agent
# Solution: Update agent capability descriptions

# More specific capabilities
agents = {
    "Analyst": "Python expert, pandas, matplotlib, statistical analysis",
    "Researcher": "Web search, fact verification, citation management"
}
```

---

## Best Practices

### 1. Clear Agent Roles

```python
# Good: Specific, non-overlapping
"Researcher": "Web search and fact-finding specialist"
"Analyst": "Data processing and statistical analysis expert"

# Bad: Vague, overlapping
"Researcher": "Finds information"
"Analyst": "Analyzes things"
```

### 2. Rich Handoff Context

```python
# Good: Structured, complete
handoff = HandoffContext(
    work_completed="Gathered 50 data points on market trends...",
    artifacts={"data.csv": data, "sources.md": citations},
    remaining_objectives=[
        "Calculate correlation coefficients",
        "Create time-series visualizations",
        "Identify statistically significant patterns"
    ],
    success_criteria=[
        "Correlation > 0.7 for key variables",
        "Visualizations show clear trends",
        "Statistical significance p < 0.05"
    ]
)

# Bad: Vague, incomplete
handoff = HandoffContext(
    work_completed="Did some research",
    artifacts={},
    remaining_objectives=["Finish the analysis"],
    success_criteria=["Make it good"]
)
```

### 3. Quality Gates

```python
# Add checkpoints before critical handoffs
if handoff.from_agent == "Researcher":
    # Verify data quality before analyst handoff
    if not self._validate_research_quality(handoff):
        return await self._request_refinement(handoff)

# Proceed with handoff only if quality passes
return handoff
```

### 4. Monitoring

```python
# Track handoff metrics
@dataclass
class HandoffMetrics:
    evaluation_time: float
    package_creation_time: float
    success: bool
    quality_improvement: float

# Log for analysis
logger.info(f"Handoff metrics: {metrics}")
```

---

## Examples

See `examples/` directory for complete examples:

- `examples/handoff_research_analysis.py` - Research to analysis handoff
- `examples/adaptive_execution.py` - Adaptive mode switching
- `examples/capability_matching.py` - Capability-based routing
- `examples/multi_agent_collaboration.py` - Complex multi-agent workflows

---

## Reference Documentation

- **Detailed Plan**: `docs/reports/DSPY_GEPA_HANDOFF_IMPROVEMENT_PLAN.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **API Reference**: `docs/API_REFERENCE.md`
- **DSPy Guide**: https://github.com/stanfordnlp/dspy

---

## Getting Help

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Documentation**: `docs/` directory
- **Examples**: `examples/` directory

---

**Last Updated:** 2025-11-06
**Version:** 1.0
**Status:** Proposal - Ready for Implementation
