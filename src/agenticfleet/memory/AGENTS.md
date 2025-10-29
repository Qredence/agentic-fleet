# Memory System Agents Documentation

## Overview

The AgenticFleet Memory System provides intelligent memory management capabilities that integrate seamlessly with your agent workflows. This document outlines the memory-related agents, their configurations, and integration patterns for enabling persistent learning and context-aware agent behavior.

## Memory System Architecture

### Core Components

- **MemoryManager**: Primary interface for memory storage and retrieval operations
- **MemoryContextProvider**: Context injection for agent conversations
- **OpenMemoryMCPIntegration**: Persistent storage via OpenMemory MCP server
- **MemoryWorkflowIntegration**: Workflow lifecycle memory management

### Memory Types

The system supports 8 distinct memory types:

1. **CONVERSATION**: Dialogue history and agent interactions
2. **LEARNING**: Lessons learned and insights from execution
3. **PATTERN**: Reusable workflows and best practices
4. **PREFERENCE**: User preferences and configuration settings
5. **CONTEXT**: Project-specific knowledge and background
6. **ERROR**: Error solutions and troubleshooting patterns
7. **TOOL_USAGE**: Tool interaction patterns and optimizations
8. **WORKFLOW**: Workflow execution patterns and optimizations

## Memory-Enhanced Agent Configuration

### Basic Memory Integration

Add memory capabilities to any agent by including the MemoryContextProvider:

```python
from agenticfleet.memory import MemoryManager, MemoryContextProvider

# Initialize memory system
memory_manager = MemoryManager()
await memory_manager.initialize()

# Create memory-enhanced context provider
context_provider = MemoryContextProvider(
    memory_manager=memory_manager,
    max_memories_per_context=5,
    enable_learning_memories=True,
    enable_context_memories=True,
    enable_error_memories=True,
)

# In your workflow factory
def create_memory_enhanced_agent(agent_config):
    # Standard agent creation
    agent = ChatAgent(
        chat_client=client,
        instructions=agent_config["instructions"],
        name=agent_config["name"],
        # ... other agent parameters
    )

    # Add memory context injection
    agent.context_provider = context_provider

    return agent
```

### Advanced Memory Configuration

Configure memory behavior per agent type:

```yaml
# agents/memory_enhanced_coder/config.yaml
agent:
  name: "memory_enhanced_coder"
  model: "gpt-5-mini"
  instructions: |
    You are a coding assistant with access to previous learnings
    and error solutions. Use provided memories to improve your
    code quality and avoid repeating mistakes.

# Memory-specific configuration
memory_config:
  enable_memories: true
  memory_types: ["learning", "error", "pattern", "conversation"]
  max_memories: 8
  store_conversations: true
  store_learnings: true
  store_errors: true
  store_patterns: false

  # Memory retrieval settings
  retrieval_threshold: 0.6
  prioritize_recent: true
  prioritize_frequently_accessed: true

  # Auto-detection settings
  auto_detect_learnings: true
  auto_detect_patterns: false
  auto_detect_errors: true
```

## Memory Agent Types

### 1. Learning Agent

Specialized in identifying and storing learnings from agent executions:

```python
class LearningAgent(ChatAgent):
    """Agent that captures and organizes learnings from conversations."""

    async def process_message(self, message: str):
        # Standard processing
        response = await super().process_message(message)

        # Detect and store learnings
        learnings = self._detect_learnings(message, response)
        for learning in learnings:
            await self.context_provider.store_learning_memory(
                agent_name=self.name,
                learning=learning["content"],
                context=learning.get("context"),
                importance_level=learning.get("importance", "medium"),
                tags=learning.get("tags", [])
            )

        return response

    def _detect_learnings(self, message: str, response: str) -> List[Dict]:
        """Extract learning insights from conversation."""
        learnings = []

        # Learning detection patterns
        indicators = [
            "i learned", "i discovered", "i found that", "key insight",
            "important lesson", "best practice", "effective approach"
        ]

        response_lower = response.lower()
        for indicator in indicators:
            if indicator in response_lower:
                # Extract learning content around indicator
                start_idx = response_lower.find(indicator)
                learning_content = response[
                    max(0, start_idx-50):min(len(response), start_idx+200)
                ].strip()

                learnings.append({
                    "content": learning_content,
                    "context": f"User: {message[:100]}...",
                    "importance": "high",
                    "tags": ["learning", self.name]
                })

        return learnings
```

### 2. Pattern Recognition Agent

Identifies and stores reusable patterns from agent workflows:

```python
class PatternRecognitionAgent(ChatAgent):
    """Agent that detects and documents reusable patterns."""

    async def execute_workflow(self, workflow_task: str):
        # Execute workflow
        result = await super().execute_workflow(workflow_task)

        # Detect patterns in execution
        patterns = await self._detect_patterns(workflow_task, result)

        for pattern in patterns:
            if self._should_store_pattern(pattern):
                await self.context_provider.store_pattern_memory(
                    agent_name=self.name,
                    pattern_name=pattern["name"],
                    pattern_description=pattern["description"],
                    usage_example=pattern.get("example"),
                    tags=pattern.get("tags", [])
                )

        return result

    def _detect_patterns(self, task: str, result: str) -> List[Dict]:
        """Identify reusable patterns in task execution."""
        patterns = []

        # Pattern detection logic
        pattern_indicators = [
            "this approach can be reused", "general pattern", "template for",
            "reusable solution", "standard approach", "best practice is"
        ]

        for indicator in pattern_indicators:
            if indicator in result.lower():
                pattern = {
                    "name": f"Pattern from {self.name}",
                    "description": self._extract_pattern_description(result, indicator),
                    "example": f"Task: {task[:100]}...",
                    "tags": ["pattern", self.name, "reusable"]
                }
                patterns.append(pattern)

        return patterns
```

### 3. Error Solution Agent

Captures and organizes error solutions for future reference:

```python
class ErrorSolutionAgent(ChatAgent):
    """Agent that captures error solutions and troubleshooting patterns."""

    async def handle_error(self, error: Exception, context: str) -> str:
        # Handle the error
        solution = await self._generate_error_solution(error, context)

        # Store error-solution pair for future reference
        await self.context_provider.store_error_memory(
            agent_name=self.name,
            error_description=str(error),
            solution=solution,
            error_type=type(error).__name__,
            context=context
        )

        return solution

    async def retrieve_similar_errors(
        self,
        error_description: str
    ) -> List[Dict]:
        """Retrieve similar error solutions from memory."""
        results = await self.context_provider.memory_manager.retrieve_memories(
            query=error_description,
            memory_types=[MemoryType.ERROR],
            limit=5
        )

        return [{
            "error": memory.content,
            "solution": self._extract_solution(memory.content),
            "type": memory.metadata.get("error_type", "unknown"),
            "access_count": memory.metadata.access_count
        } for memory in results.memories]
```

### 4. Context-Aware Agent

Agent that maintains and utilizes project context:

```python
class ContextAwareAgent(ChatAgent):
    """Agent that maintains and utilizes project-specific context."""

    async def initialize_project_context(self, project_path: str):
        """Analyze project structure and store context."""
        project_context = await self._analyze_project(project_path)

        await self.context_provider.memory_manager.store_memory(
            title=f"Project Context - {project_path}",
            content=project_context["description"],
            memory_type=MemoryType.CONTEXT,
            priority=MemoryPriority.HIGH,
            context_keywords=project_context["keywords"],
            metadata={
                "project_path": project_path,
                "structure": project_context["structure"],
                "technologies": project_context["technologies"]
            }
        )

        return project_context

    async def get_relevant_context(
        self,
        task_description: str
    ) -> List[Dict]:
        """Retrieve project-relevant context for task execution."""
        results = await self.context_provider.memory_manager.retrieve_memories(
            query=task_description,
            memory_types=[MemoryType.CONTEXT, MemoryType.PATTERN],
            limit=10,
            min_relevance_score=0.7
        )

        return [{
            "type": memory.type.value,
            "title": memory.title,
            "content": memory.content,
            "relevance": memory.metadata.relevance_score
        } for memory in results.memories]
```

## Workflow Integration Patterns

### 1. Memory-Enhanced Workflow Factory

```python
from agenticfleet.memory.workflow_integration import MemoryWorkflowIntegration

async def create_memory_enhanced_workflow():
    """Create a workflow with integrated memory capabilities."""

    # Initialize memory components
    memory_manager = MemoryManager()
    await memory_manager.initialize()

    context_provider = MemoryContextProvider(memory_manager)
    workflow_integration = MemoryWorkflowIntegration(
        memory_manager=memory_manager,
        context_provider=context_provider
    )

    # Set global workflow integration
    from agenticfleet.memory.workflow_integration import set_workflow_integration
    set_workflow_integration(workflow_integration)

    # Create workflow with memory context
    builder = MagenticBuilder().participants(
        coder=coder_agent,  # Memory-enhanced coder
        researcher=researcher_agent,  # Memory-enhanced researcher
        reviewer=reviewer_agent,  # Memory-enhanced reviewer
    ).with_standard_manager(
        instructions="Use memory context to inform decisions and store learnings."
    )

    return builder.build()
```

### 2. Agent Memory Lifecycle Management

```python
class MemoryAwareAgent(Agent):
    """Base class for agents with integrated memory capabilities."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.memory_manager = kwargs.get('memory_manager')
        self.context_provider = kwargs.get('context_provider')
        self.workflow_id = kwargs.get('workflow_id')

    async def before_execution(self, task: str):
        """Inject memory context before execution."""
        if self.context_provider and self.workflow_id:
            context = await self.context_provider.get_context(
                conversation_id=self.workflow_id,
                agent_name=self.name,
                current_message=task
            )

            # Inject context into agent's working memory
            self.memory_context = context
            self.current_memories = context.get('memories', [])

            # Add memory context to task prompt
            if self.current_memories:
                memory_prompt = self._format_memory_context(self.current_memories)
                task = f"{memory_prompt}\n\nCurrent Task: {task}"

        return task

    async def after_execution(self, task: str, result: str):
        """Store execution learnings and context."""
        if self.context_provider and self.workflow_id:
            # Store conversation memory
            await self.context_provider.store_conversation_memory(
                conversation_id=self.workflow_id,
                agent_name=self.name,
                message=task,
                response=result
            )

            # Detect and store additional memory types
            await self._store_execution_memories(task, result)

    def _format_memory_context(self, memories: List[Dict]) -> str:
        """Format memories for inclusion in agent context."""
        if not memories:
            return ""

        context_parts = ["## Relevant Memories and Context\n"]

        for memory in memories:
            context_parts.append(f"""
### {memory['title']} ({memory['type'].upper()})
Priority: {memory['priority']}
Created: {memory['created_at']}

{memory['content']}
""")

        return "\n".join(context_parts)
```

## Memory System Configuration

### Environment Variables

Configure memory system behavior via environment variables:

```bash
# .env
AGENTICFLEET_MEMORY_OPENMEMORY_ENABLED=true
AGENTICFLEET_MEMORY_MAX_MEMORIES_PER_CONTEXT=10
AGENTICFLEET_MEMORY_ENABLE_LEARNING_MEMORIES=true
AGENTICFLEET_MEMORY_RETENTION_DAYS_LEARNING=90
AGENTICFLEET_MEMORY_AUTO_CLEANUP_INTERVAL_HOURS=24
```

### Agent-Specific Memory Settings

Configure memory behavior per agent type:

```python
# src/agenticfleet/memory/config.py
memory_config.set_agent_config("coder_agent", {
    "enable_memories": True,
    "memory_types": ["learning", "error", "pattern", "conversation"],
    "max_memories": 8,
    "store_conversations": True,
    "store_learnings": True,
    "store_errors": True,
    "store_patterns": False,
    "retrieval_threshold": 0.6
})

memory_config.set_agent_config("researcher_agent", {
    "enable_memories": True,
    "memory_types": ["learning", "context", "conversation"],
    "max_memories": 5,
    "store_conversations": True,
    "store_learnings": True,
    "store_errors": False,
    "store_patterns": False,
    "retrieval_threshold": 0.7
})
```

## Performance and Monitoring

### Memory Statistics

Monitor memory system performance:

```python
async def monitor_memory_system():
    """Monitor memory system health and performance."""
    stats = await memory_manager.get_memory_stats()

    return {
        "total_memories": stats.total_memories,
        "storage_usage_mb": stats.storage_usage_mb,
        "average_access_count": stats.average_access_count,
        "memory_types": stats.memories_by_type,
        "priorities": stats.memories_by_priority,
        "most_accessed": stats.most_accessed_memories[:10],
        "recently_created": stats.recently_created
    }
```

### Memory Optimization

Implement memory cleanup and optimization:

```python
async def optimize_memory_system():
    """Optimize memory system for performance."""
    # Get current stats
    stats = await memory_manager.get_memory_stats()

    # Cleanup old memories based on retention policy
    cleanup_count = 0
    for memory_type, retention_days in [
        (MemoryType.CONVERSATION, 30),
        (MemoryType.ERROR, 60),
        (MemoryType.LEARNING, 90),
        (MemoryType.PATTERN, 180)
    ]:
        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        # Find and delete old memories
        old_memories = [
            m for m in all_memories
            if m.type == memory_type and m.metadata.created_at < cutoff
        ]

        for memory in old_memories:
            await memory_manager.delete_memory(memory.id)
            cleanup_count += 1

    return {
        "cleanup_count": cleanup_count,
        "remaining_memories": stats.total_memories - cleanup_count
    }
```

## Testing Memory-Enhanced Agents

### Unit Testing Memory Integration

```python
@pytest.mark.asyncio
async def test_memory_enhanced_agent():
    """Test that memory-enhanced agents properly use context."""

    # Setup
    memory_manager = MemoryManager()
    await memory_manager.initialize()

    context_provider = MemoryContextProvider(memory_manager)

    # Store test memories
    await memory_manager.store_memory(
        title="Python Async Best Practices",
        content="Always use await with async functions",
        memory_type=MemoryType.LEARNING,
        context_keywords=["python", "async"]
    )

    # Create agent
    agent = MemoryAwareAgent(
        name="test_agent",
        memory_manager=memory_manager,
        context_provider=context_provider,
        workflow_id="test_workflow"
    )

    # Test context injection
    task = await agent.before_execution("How should I handle async in Python?")

    # Verify memory context is included
    assert "Relevant Memories" in task
    assert "async" in task.lower()
```

### Integration Testing Memory Workflows

```python
@pytest.mark.asyncio
async def test_memory_workflow_integration():
    """Test complete memory integration in workflows."""

    workflow_integration = MemoryWorkflowIntegration(
        memory_manager=MemoryManager(),
        context_provider=MemoryContextProvider(MemoryManager())
    )

    # Initialize workflow
    await workflow_integration.initialize_workflow("test_workflow", [])

    # Simulate agent execution
    memory_ids = await workflow_integration.store_agent_execution(
        workflow_id="test_workflow",
        agent_name="test_agent",
        task="Learn about async programming",
        result="Key learning: Always use await with async functions"
    )

    # Verify memories were stored
    stats = await workflow_integration.memory_manager.get_memory_stats()
    assert stats.total_memories >= 1

    # Test context retrieval
    context = await workflow_integration.provide_agent_context(
        workflow_id="test_workflow",
        agent_name="test_agent",
        current_message="Help with async programming"
    )

    assert "memories" in context
    assert context["memory_count"] >= 0
```

## Best Practices

### 1. Memory Management

- **Use appropriate memory types** for different kinds of information
- **Set meaningful context keywords** to improve search relevance
- **Configure retention policies** based on memory type importance
- **Monitor storage usage** and implement cleanup policies

### 2. Agent Integration

- **Inject context before execution** to inform agent decisions
- **Store learnings after execution** to capture insights
- **Use agent-specific configurations** for tailored memory behavior
- **Implement error memory capture** for troubleshooting

### 3. Performance Optimization

- **Limit memories per context** to prevent context overload
- **Use local caching** for frequently accessed memories
- **Implement intelligent cleanup** based on access patterns
- **Monitor memory growth** and adjust retention policies

### 4. Privacy and Security

- **Avoid storing sensitive information** in memories
- **Implement access controls** for shared memory systems
- **Use appropriate retention policies** for different data types
- **Monitor memory content** for compliance requirements

## Troubleshooting

### Common Issues

**Memory not being retrieved**:

- Check memory type configuration
- Verify context keywords match search queries
- Ensure retention policies haven't deleted memories

**Slow performance**:

- Reduce max memories per context
- Enable local caching
- Implement cleanup for old memories

**Storage usage too high**:

- Adjust retention policies
- Implement automatic cleanup
- Monitor and optimize memory content

### Debug Commands

```bash
# Check memory system status
uv run fleet memory status

# List recent memories
uv run fleet memory search "recent" --limit 10

# Test memory system
uv run fleet memory test

# View memory statistics
uv run fleet memory stats
```

This documentation provides a comprehensive guide for integrating the AgenticFleet Memory System with your agents, enabling persistent learning, context-aware behavior, and intelligent memory management across your workflows.
