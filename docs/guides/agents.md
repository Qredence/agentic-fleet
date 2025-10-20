# Working with Agents

Learn how to use, customize, and extend AgenticFleet's specialist agents.

---

## Agent Overview

AgenticFleet includes four types of agents:

| Agent | Purpose | Default Model | Key Tools |
|-------|---------|---------------|-----------|
| **Orchestrator** | Plans, delegates, synthesizes | `gpt-5` | None (manager role) |
| **Researcher** | Information gathering, research | `gpt-5` | web_search_tool |
| **Coder** | Code generation, execution | `gpt-5-codex` | code_interpreter_tool |
| **Analyst** | Data analysis, visualization | `gpt-5` | data_analysis_tool, visualization_suggestion_tool |

---

## The Orchestrator

### Role

The orchestrator (manager) coordinates all other agents:

- Creates structured plans
- Evaluates progress
- Delegates tasks to specialists
- Synthesizes final answers
- Handles replanning when stuck

### Configuration

Location: `src/agenticfleet/config/workflow.yaml`

```yaml
fleet:
  manager:
    model: gpt-5
    temperature: 0.2
    max_tokens: 4096
    instructions: |
      You are the orchestrator for a multi-agent system.

      Your responsibilities:
      1. Break down complex tasks into steps
      2. Identify which specialist agent should handle each step
      3. Track progress and replan if needed
      4. Synthesize agent responses into coherent answers

      Available agents:
      - researcher: Information gathering and research
      - coder: Code generation and execution
      - analyst: Data analysis and visualization insights
```

### When to Customize

Modify orchestrator instructions to:
- Change delegation strategy
- Adjust planning format
- Define termination criteria
- Add domain-specific guidance

**Example:** Prioritize code generation

```yaml
instructions: |
  When tasks involve programming, prefer delegating to coder first.
  Only use researcher for gathering external documentation.
```

---

## The Researcher Agent

### Purpose

Specialized in information gathering, research, and summarization.

### Capabilities

- Web search (mock by default)
- Document summarization
- Source citation
- Fact verification

### Configuration

Location: `src/agenticfleet/agents/researcher/config.yaml`

```yaml
agent:
  name: researcher
  model: gpt-5
  temperature: 0.2
  system_prompt: |
    You are a specialized research agent.

    When given a research task:
    1. Use web_search_tool to find relevant information
    2. Analyze and summarize findings
    3. Cite sources when applicable
    4. Present information clearly and concisely

    Available tools: web_search_tool

  tools:
    - name: web_search_tool
      enabled: true
```

### Example Tasks

```
# Simple research
What are the benefits of microservices architecture?

# Comparative research
Compare Python vs Go for backend development

# Technical research
Explain the latest transformer model architectures
```

### Customization

#### Add Domain Expertise

```yaml
system_prompt: |
  You are a medical research specialist.
  Focus on peer-reviewed sources and clinical evidence.
  Always cite study references.
```

#### Adjust Search Depth

```yaml
tools:
  - name: web_search_tool
    enabled: true
    config:
      max_results: 20  # More thorough search
      timeout: 60      # Longer timeout
```

---

## The Coder Agent

### Purpose

Specialized in code generation, explanation, and execution.

### Capabilities

- Generate code in multiple languages
- Explain code logic
- Execute Python code safely
- Debug and fix errors
- Provide usage examples

### Configuration

Location: `src/agenticfleet/agents/coder/config.yaml`

```yaml
agent:
  name: coder
  model: gpt-5-codex  # Specialized for code
  temperature: 0.1     # Lower for deterministic output
  system_prompt: |
    You are an expert software engineer.

    When writing code:
    1. Follow best practices and conventions
    2. Add clear comments and docstrings
    3. Include error handling
    4. Provide usage examples

    When executing code:
    1. Use code_interpreter_tool for Python
    2. Explain what the code will do
    3. Handle errors gracefully

    Available tools: code_interpreter_tool

  tools:
    - name: code_interpreter_tool
      enabled: true
      config:
        sandbox: true
        timeout: 30
```

### Example Tasks

```
# Code generation
Write a Python function to parse JSON with error handling

# Algorithm implementation
Implement quicksort in Python with O(n log n) complexity

# Code explanation
Explain how this recursive function works: [paste code]

# Debugging
Fix the bug in this code: [paste code]
```

### Customization

#### Specialized Language Focus

```yaml
system_prompt: |
  You are a TypeScript/React specialist.
  Always use TypeScript strict mode.
  Follow React best practices and hooks patterns.
```

#### Restricted Execution

```yaml
tools:
  - name: code_interpreter_tool
    config:
      allowed_modules:  # Whitelist only
        - math
        - json
        - datetime
      denied_operations:
        - file_write
        - network_access
```

---

## The Analyst Agent

### Purpose

Specialized in data analysis, statistical insights, and visualization recommendations.

### Capabilities

- Data interpretation
- Statistical analysis suggestions
- Visualization recommendations
- Pattern recognition
- Insight generation

### Configuration

Location: `src/agenticfleet/agents/analyst/config.yaml`

```yaml
agent:
  name: analyst
  model: gpt-5
  temperature: 0.3
  system_prompt: |
    You are a data analysis specialist.

    When analyzing data:
    1. Identify appropriate statistical methods
    2. Suggest relevant visualizations
    3. Explain findings in business terms
    4. Provide actionable insights

    Available tools:
    - data_analysis_tool: For statistical analysis
    - visualization_suggestion_tool: For chart recommendations

  tools:
    - name: data_analysis_tool
      enabled: true
      config:
        confidence_threshold: 0.7
    - name: visualization_suggestion_tool
      enabled: true
```

### Example Tasks

```
# Analysis recommendation
What statistical method should I use for A/B testing?

# Visualization guidance
What charts best show quarterly revenue trends?

# Data interpretation
Analyze this dataset for customer churn patterns

# Insight generation
What metrics should I track for SaaS business growth?
```

### Customization

#### Domain-Specific Analysis

```yaml
system_prompt: |
  You are a financial data analyst.
  Focus on risk metrics, portfolio optimization, and market analysis.
  Always consider regulatory compliance (SOX, GDPR).
```

#### Adjust Confidence Thresholds

```yaml
tools:
  - name: data_analysis_tool
    config:
      confidence_threshold: 0.9  # Higher bar for recommendations
      min_sample_size: 1000       # Require sufficient data
```

---

## Agent Collaboration

### How Agents Work Together

1. **Orchestrator receives task**
   ```
   User: "Research Python web frameworks and write example code"
   ```

2. **Orchestrator creates plan**
   ```
   Plan:
   1. Delegate to researcher to find framework options
   2. Have coder write example code
   3. Synthesize findings
   ```

3. **Researcher gathers information**
   ```
   Researcher: "Popular frameworks: Flask, FastAPI, Django..."
   ```

4. **Coder generates examples**
   ```
   Coder: "Here's a FastAPI example: [code]"
   ```

5. **Orchestrator synthesizes**
   ```
   Result: Complete answer with research + code
   ```

### Multi-Agent Patterns

#### Sequential Delegation

```
Task → Researcher → Coder → Analyst → Result
```

**Example:** "Research ML algorithms, implement one, analyze performance"

#### Parallel Consultation

```
Task → [Researcher + Coder + Analyst] → Synthesize → Result
```

**Example:** "Quick opinions from all agents on system architecture"

#### Iterative Refinement

```
Task → Agent A → Review → Agent B → Refine → Agent A → Result
```

**Example:** "Coder writes code, researcher reviews, coder improves"

---

## Advanced Customization

### Creating Agent Variants

Create a specialized researcher variant:

```bash
# 1. Copy existing agent
cp -r src/agenticfleet/agents/researcher src/agenticfleet/agents/medical_researcher

# 2. Update config
nano src/agenticfleet/agents/medical_researcher/config.yaml
```

```yaml
agent:
  name: medical_researcher
  model: gpt-5
  system_prompt: |
    You are a medical research specialist with expertise in:
    - Clinical trials and evidence-based medicine
    - Medical literature review and meta-analysis
    - Healthcare data analysis

    Always:
    - Cite peer-reviewed sources
    - Consider clinical relevance
    - Note study limitations
```

```python
# 3. Register in fleet_builder.py
from agenticfleet.agents.medical_researcher import create_medical_researcher_agent

def build_fleet():
    builder = FleetBuilder()
    builder.with_agents([
        create_orchestrator_agent(),
        create_medical_researcher_agent(),  # Add custom agent
        create_coder_agent(),
        create_analyst_agent(),
    ])
    return builder.build()
```

### Custom System Prompts

Best practices for writing system prompts:

```yaml
system_prompt: |
  # 1. Role definition
  You are a [specific role] with expertise in [domain].

  # 2. Capabilities
  Your core capabilities include:
  - [Capability 1]
  - [Capability 2]

  # 3. Guidelines
  When performing tasks:
  1. [Guideline 1]
  2. [Guideline 2]

  # 4. Available tools
  Available tools: [tool1], [tool2]

  # 5. Output format (optional)
  Always structure responses as:
  - Summary
  - Detailed findings
  - Recommendations
```

### Model Selection

Choose models based on agent needs:

```yaml
# For factual tasks - standard models
researcher:
  model: gpt-4o  # Balanced performance

# For code - specialized models
coder:
  model: gpt-5-codex  # Optimized for code

# For reasoning - o1 series
analyst:
  model: o1-preview
  reasoning_effort: high  # Deep analysis
```

---

## Monitoring Agent Performance

### Enable Agent Logging

```yaml
# workflow.yaml
callbacks:
  tool_monitoring: true
  plan_logging: true
```

### View Agent Activity

```bash
# Real-time logs
tail -f logs/agenticfleet.log

# Filter by agent
grep "researcher" logs/agenticfleet.log

# Check tool usage
grep "tool_call" logs/agenticfleet.log
```

### Performance Metrics

Track in logs:
- Agent selection frequency
- Tool execution success rate
- Average response time
- Token usage per agent

---

## Troubleshooting

### Agent Not Responding

**Problem:** Agent selected but no output

**Solutions:**
1. Check agent config exists
2. Verify model accessibility
3. Check tool imports
4. Review system prompt syntax

```bash
# Validate configuration
make test-config

# Check specific agent
uv run python -c "from agenticfleet.agents.researcher import create_researcher_agent; create_researcher_agent()"
```

### Wrong Agent Selected

**Problem:** Orchestrator delegates to incorrect agent

**Solution:** Improve orchestrator instructions

```yaml
manager:
  instructions: |
    Agent selection guidelines:
    - researcher: Information gathering, external knowledge
    - coder: Code generation, programming tasks, debugging
    - analyst: Data analysis, statistics, visualizations

    Be explicit about which agent to use based on task type.
```

### Tool Execution Failures

**Problem:** Agent tries to use tool but fails

**Solutions:**
```yaml
# Enable tool
tools:
  - name: problematic_tool
    enabled: true  # Check this is true

# Add error handling
config:
  retry_on_error: true
  max_retries: 3
```

---

## Best Practices

### Agent Design

1. **Single Responsibility** – Each agent has one clear purpose
2. **Clear Boundaries** – Distinct capabilities, minimal overlap
3. **Tool Focus** – Agents defined by their tools
4. **Prompt Clarity** – Explicit instructions, no ambiguity

### Performance

1. **Model Selection** – Match model to task complexity
2. **Temperature Tuning** – Lower for deterministic tasks
3. **Token Limits** – Set appropriate max_tokens
4. **Streaming** – Enable for better UX

### Maintenance

1. **Version Prompts** – Track prompt changes in git
2. **Test Configs** – Validate after every change
3. **Monitor Usage** – Track which agents are used most
4. **Iterate** – Refine based on real usage patterns

---

## Next Steps

- **[Tool Development](../advanced/tool-development.md)** – Create custom agent tools
- **[HITL Integration](human-in-the-loop.md)** – Add approval flows
- **[Workflow Customization](../advanced/workflow-customization.md)** – Build custom patterns

---

**Questions?** See [Troubleshooting](../runbooks/troubleshooting.md) or ask in [Discussions](https://github.com/Qredence/agentic-fleet/discussions).
