# Prompt Kit Integration Guide

This document describes the Prompt Kit integration in AgenticFleet, including usage patterns, component architecture, and future enhancements.

## Overview

AgenticFleet now uses official [Prompt Kit](https://www.prompt-kit.com/) components for displaying reasoning traces and chain-of-thought orchestrator messages. Prompt Kit is a React component library specifically designed for AI interfaces, providing high-quality, accessible, and customizable components.

## Components

### ChainOfThought

**Location**: `src/frontend/src/components/chat/ChainOfThought.tsx`

**Purpose**: Displays orchestrator/manager messages as collapsible steps, showing the agent's planning and progress evaluation.

**Key Features**:

- Collapsible steps with auto-expand for latest message
- Icon-based message type indicators:
  - `ListChecks` (task_ledger): Task planning
  - `Clock` (progress_ledger): Progress evaluation
  - `Lightbulb` (facts): Facts and reasoning
  - `Info` (default): Manager updates
- Timestamp display with seconds precision
- Markdown content rendering via `StructuredMessageContent`

**Usage**:

```tsx
<ChainOfThought messages={orchestratorMessages} />
```

**Event Mapping**:

- Backend: `orchestrator.message` events with `kind` field
- Frontend: `OrchestratorMessage[]` with `{id, message, kind, timestamp}`

### ReasoningDisplay

**Location**: `src/frontend/src/components/chat/ReasoningDisplay.tsx`

**Purpose**: Displays model reasoning traces with auto-close behavior when streaming completes.

**Key Features**:

- Two display modes:
  1. **Section-based**: Multiple reasoning sections from orchestrator
  2. **Content-based**: Raw reasoning content from o1/o3 models
- Auto-close when `isStreaming` changes to false

- Markdown rendering with smart truncation
- Brain/Lightbulb icons based on content type

**Usage**:

```tsx
// Section-based (orchestrator reasoning)
<ReasoningDisplay
  sections={reasoningSections}
  isStreaming={isCurrentlyStreaming}
/>

// Content-based (o1/o3 reasoning tokens)
<ReasoningDisplay
  content={reasoningContent}
  isStreaming={isCurrentlyStreaming}
  triggerText="Model reasoning"
/>
```

**Future**: Ready for o1/o3 reasoning token display when backend support is added.

## Type System

### Updated Types

**ChatMessage** (`types/chat.ts`):

```typescript
interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: number;
  agentId?: string;

  reasoning?: string; // NEW: o1/o3 reasoning content
  reasoningStreaming?: boolean; // NEW: reasoning streaming state
}
```

**SSEEventType** (`types/chat.ts`):

```typescript
type SSEEventType =
  | "response.delta"
  | "response.completed"
  | "orchestrator.message"
  | "agent.message.complete"
  | "reasoning.delta" // NEW: reasoning streaming
  | "reasoning.completed" // NEW: reasoning complete
  | "error";
```

## Installation

Prompt Kit components are installed via shadcn CLI:

```bash
# From src/frontend directory
npx shadcn@latest add https://www.prompt-kit.com/c/reasoning.json
npx shadcn@latest add https://www.prompt-kit.com/c/chain-of-thought.json
```

**Configuration**: The `components.json` file was updated to remove the unsupported `registries` field for compatibility with Prompt Kit and shadcn CLI.

> Note: The `registries` field is no longer supported by the shadcn CLI ([see releases](https://github.com/shadcn-ui/ui/releases)), and may cause installation errors with new component sources if present.

## Backend Integration

### Current State

The backend already configures reasoning parameters for o1/o3 models:

**Configuration** (`src/agentic_fleet/core/magentic_agent.py`):

```python
OpenAIResponsesClient(

    model_id=model_id,
    reasoning_effort=reasoning_effort,  # "low", "medium", "high"
    reasoning_verbosity=reasoning_verbosity,  # "normal", "verbose"
    # ...
)
```

**Agent Configuration** (`agents/*/config.yaml`):

```yaml
reasoning:
  effort: "high"
  verbosity: "verbose"
```

### Event Structure

**Current Events**:

- `message.delta`: Content streaming
- `agent.message.complete`: Agent work completion
- `orchestrator.message`: Manager messages with `kind` field

**Future Events** (for o1/o3 reasoning):

- `reasoning.delta`: Reasoning token streaming
- `reasoning.completed`: Reasoning trace complete

## Frontend State Management

### Chat Store

**Current**: Handles content streaming and orchestrator messages

**Future Enhancement**: Add reasoning buffer to track streaming reasoning content:

```typescript
interface ChatState {
  // ... existing fields
  currentReasoningContent?: string;
  currentReasoningStreaming?: boolean;
}
```

### SSE Handler

**Location**: `src/frontend/src/lib/api/chat.ts` (streamChatResponse)

**Current**: Handles `response.delta`, `agent.message.complete`, `orchestrator.message`

**Future**: Add handlers for `reasoning.delta` and `reasoning.completed`:

```typescript
case "reasoning.delta":
  // Append to reasoning buffer
  store.appendReasoningDelta(event.reasoning);
  break;

case "reasoning.completed":
  // Mark reasoning complete, trigger auto-close
  store.completeReasoning();
  break;
```

## UI Patterns

### Auto-Close Behavior

The Reasoning component automatically closes when streaming completes:

```tsx
<Reasoning isStreaming={currentStreamingMessageId !== null}>
  {/* Content auto-closes when isStreaming becomes false */}
</Reasoning>
```

### Collapsible Steps

ChainOfThought steps are collapsible with the latest step auto-expanded:

```tsx
<ChainOfThoughtStep defaultOpen={index === messages.length - 1}>
  <ChainOfThoughtTrigger leftIcon={icon}>{title}</ChainOfThoughtTrigger>
  <ChainOfThoughtContent>{content}</ChainOfThoughtContent>
</ChainOfThoughtStep>
```

### Markdown Rendering

Both components support markdown rendering:

```tsx
<ReasoningContent markdown>{markdownContent}</ReasoningContent>
```

## Testing

### Current Coverage

- Frontend linting: ✅ Clean
- TypeScript compilation: ✅ Passing
- Production build: ✅ 4.13s

### Integration Testing

When adding reasoning token support, test:

1. **Streaming behavior**: Reasoning opens automatically when streaming starts
2. **Auto-close**: Reasoning closes when streaming completes
3. **Content accumulation**: Reasoning deltas properly append
4. **Error handling**: Invalid reasoning content handled gracefully

### Visual Testing

Verify:

- Icon display and colors
- Collapsible animation smoothness
- Markdown rendering correctness
- Timestamp formatting
- Mobile responsiveness

## Future Enhancements

### Phase 1: Backend Reasoning Token Exposure

1. Update `WorkflowEventBridge.convert_event()` to handle reasoning content
2. Emit `reasoning.delta` events during o1/o3 streaming
3. Emit `reasoning.completed` when reasoning trace finishes
4. Add reasoning content to `MagenticAgentDeltaEvent`

### Phase 2: Frontend Reasoning Display

1. Add reasoning state to chat store
2. Handle reasoning events in SSE parser
3. Wire reasoning content to ReasoningDisplay
4. Add user preference for auto-collapse vs. always-open

### Phase 3: Advanced Features

1. Reasoning trace export (JSON, markdown)
2. Highlighting and annotation
3. Reasoning step breakpoints for debugging
4. Performance metrics (reasoning time, token count)

## Best Practices

### Component Usage

1. **Always pass isStreaming**: Enables auto-close behavior
2. **Provide meaningful trigger text**: Helps users understand content type
3. **Use appropriate icons**: Match icon to message kind
4. **Keep content concise**: Use truncation for long traces
5. **Test with real data**: Verify behavior with actual backend events

### Performance

1. **Avoid unnecessary re-renders**: Memoize expensive computations
2. **Lazy load reasoning content**: Only load when user expands
3. **Limit history**: Cap orchestrator message count in store
4. **Debounce updates**: Batch rapid reasoning deltas

### Accessibility

1. **Keyboard navigation**: All components support keyboard control
2. **Screen readers**: Proper ARIA labels and roles
3. **Focus management**: Focus moves correctly on expand/collapse
4. **Color contrast**: Icons and text meet WCAG standards

## References

- [Prompt Kit Documentation](https://www.prompt-kit.com/docs)
- [Reasoning Component](https://www.prompt-kit.com/docs/reasoning)
- [ChainOfThought Component](https://www.prompt-kit.com/docs/chain-of-thought)
- [Agent Framework Documentation](https://github.com/microsoft/agent-framework)
- [OpenAI o1/o3 Reasoning](https://platform.openai.com/docs/guides/reasoning)

## Change History

Integrated as part of the v0.5.6 release:

- ChainOfThought component with collapsible steps
- ReasoningDisplay component (single final reasoning trace, no incremental deltas)
- Type system updates adding optional `reasoning` field and `reasoning.completed` event
- Frontend quality improvements and auto-close reasoning behavior
