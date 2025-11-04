# Structured Message UI - Steps, Chain of Thoughts, and Reasoning

## Overview

The AgenticFleet frontend now intelligently parses and displays agent and orchestrator messages using structured patterns:

- **Steps**: Task plans, numbered lists, and bullet-point workflows
- **Reasoning**: Explanations, rationales, and "why" sections
- **Chain of Thought**: Sequential reasoning flow with fact accumulation

## Architecture

### Components

#### Display Components (`src/frontend/src/components/chat/`)

1. **StepsDisplay.tsx**
   - Wraps PromptKit `Steps` components
   - Displays numbered/bulleted lists with collapsible substeps
   - Auto-expands during streaming
   - Visual hierarchy with step numbering

2. **ReasoningDisplay.tsx**
   - Wraps PromptKit `Reasoning` components
   - Shows explanation sections with markdown support
   - Lightbulb icon for visual distinction
   - Auto-opens during streaming

3. **ChainOfThoughtDisplay.tsx**
   - Wraps PromptKit `ChainOfThought` components
   - Timeline visualization with colored thought nodes
   - Types: fact (blue), deduction (amber), decision (green)
   - Sequential flow with visual connectors

4. **StructuredMessageContent.tsx**
   - Main orchestrator component
   - Calls message parser to detect patterns
   - Routes to appropriate display component
   - Handles mixed content and fallback to markdown

#### Parser (`src/frontend/src/lib/parsers/messageParser.ts`)

**Pattern Detection Functions:**

- `detectPattern()`: Analyzes content and returns pattern type
- `parseSteps()`: Extracts numbered/bulleted lists
- `parseReasoning()`: Finds reasoning sections
- `parseChainOfThought()`: Identifies sequential thoughts
- `parseMessage()`: Main entry point returning `ParsedMessage`

**Detection Logic:**

- **Steps**: `1.`, `-`, `•`, `*` at line start, or "Plan:", "Steps:" headers
- **Reasoning**: "Reason:", "Explanation:", "Because:", "Rationale:", "Why:"
- **Chain of Thought**: "First,", "Then,", "Next,", "Given...", "Therefore..."

#### Types (`src/frontend/src/types/chat.ts`)

```typescript
type MessagePattern =
  | "steps"
  | "reasoning"
  | "chain_of_thought"
  | "mixed"
  | "plain";

interface StepItem {
  index: number;
  content: string;
  substeps?: StepItem[];
  completed?: boolean;
}

interface ReasoningSection {
  title: string;
  content: string;
  type: "reason" | "explanation" | "rationale";
}

interface ThoughtNode {
  id: string;
  content: string;
  timestamp: number;
  type: "fact" | "deduction" | "decision";
}

interface ParsedMessage {
  pattern: MessagePattern;
  data: {
    steps?: StepItem[];
    reasoning?: ReasoningSection[];
    thoughts?: ThoughtNode[];
    plain?: string;
  };
}
```

### Integration Points

1. **ChatMessage.tsx**
   - Replaced plain `ReactMarkdown` with `StructuredMessageContent`
   - Passes `isStreaming` prop for auto-expand behavior
   - Maintains agent ID display and message actions

2. **ChainOfThought.tsx**
   - Enhanced orchestrator message display
   - Maps message `kind` to human-readable labels:
     - `task_ledger` → "Task Plan"
     - `progress_ledger` → "Progress Evaluation"
     - `facts` → "Facts & Reasoning"
   - Uses `StructuredMessageContent` for parsing

## Usage Examples

### Example 1: Steps Pattern

**Input Message:**

```
Plan:
1. Gather user requirements
2. Design system architecture
3. Implement core features
4. Test and deploy
```

**Rendered Output:**

- Collapsible "Plan (4 steps)" section
- Numbered list with visual hierarchy
- Auto-expanded during streaming

### Example 2: Reasoning Pattern

**Input Message:**

```
Reason: The user needs authentication because the application handles sensitive data.

Explanation: We'll use OAuth2 for industry-standard security and better user experience.
```

**Rendered Output:**

- Two collapsible reasoning sections
- "Reason" and "Explanation" headers with lightbulb icons
- Markdown-rendered content

### Example 3: Chain of Thought Pattern

**Input Message:**

```
First, we analyze the request to understand requirements.
Then, we check available resources and constraints.
Given these facts, we can determine the optimal approach.
Therefore, the recommendation is to use microservices architecture.
```

**Rendered Output:**

- Timeline visualization with 4 thought nodes
- Color-coded by type (fact/deduction/decision)
- Visual connectors showing sequential flow

## Testing Guide

### Manual Testing Steps

1. **Start the development server:**

   ```bash
   cd /Volumes/Samsung-SSD-T7/Workspaces/Github/qredence/agent-framework/v0.5/AgenticFleet
   make dev
   ```

2. **Test Steps Display:**
   - Send a message: "Create a plan to build a web app"
   - Verify orchestrator shows numbered plan as collapsible steps
   - Check substeps render with letter numbering

3. **Test Reasoning Display:**
   - Send a message: "Explain why microservices are better than monoliths"
   - Verify reasoning sections appear with lightbulb icons
   - Check markdown rendering in content

4. **Test Chain of Thought:**
   - Send a complex question requiring multi-step reasoning
   - Verify thought nodes appear in timeline format
   - Check color coding: blue (facts), amber (deductions), green (decisions)

5. **Test Streaming Behavior:**
   - Observe auto-expand during message streaming
   - Verify sections collapse after completion (for reasoning)
   - Check steps remain expanded by default

6. **Test Mixed Content:**
   - Send messages with multiple patterns
   - Verify all detected patterns render correctly
   - Check fallback to markdown for unstructured parts

### Automated Testing (Future)

Consider adding Vitest tests for:

- Parser pattern detection accuracy
- Component rendering with different prop combinations
- Edge cases (empty content, malformed patterns)
- Streaming state transitions

## Configuration

### Registry Configuration (`src/frontend/components.json`)

```json
{
  "registries": {
    "@prompt-kit": "https://www.prompt-kit.com/c/registry.json",
    "@motion-primitives": "https://motion-primitives.com/c/registry.json"
  }
}
```

### PromptKit Components Used

- `steps` - Collapsible step sequences
- `reasoning` - Expandable reasoning sections
- `chain-of-thought` - Timeline thought visualization

## Design Principles

1. **Auto-Expand on Streaming**: Keep users engaged with real-time updates
2. **Visual Hierarchy**: Clear distinction between pattern types
3. **Collapsible Sections**: Reduce clutter, allow focus
4. **Consistent Theme**: Matches existing shadcn/ui new-york style
5. **Accessibility**: Keyboard navigation, ARIA labels
6. **Responsive**: Works on mobile and desktop

## Future Enhancements

- [ ] Add progress indicators for completed steps
- [ ] Support nested reasoning sections
- [ ] Timeline scrubbing for long thought chains
- [ ] Export structured content as JSON/markdown
- [ ] Syntax highlighting for code in reasoning
- [ ] Animated transitions for pattern changes
- [ ] User preferences for default open/closed state

## Troubleshooting

### Patterns Not Detected

**Issue**: Message shows as plain markdown instead of structured

**Solutions**:

1. Check pattern detection logic in `messageParser.ts`
2. Verify message format matches detection regex
3. Test with simpler pattern first
4. Enable debug logging to see parsed output

### Components Not Rendering

**Issue**: Display components don't appear

**Solutions**:

1. Verify PromptKit components are installed: check `components/ui/`
2. Run `npm install` in `src/frontend/src/`
3. Check browser console for import errors
4. Verify registry URLs in `components.json`

### Streaming Not Auto-Expanding

**Issue**: Sections remain collapsed during streaming

**Solutions**:

1. Ensure `isStreaming` prop is passed correctly
2. Check `ChatPage.tsx` streaming message detection
3. Verify component default props handle streaming state

## Related Documentation

- [PromptKit Documentation](https://www.prompt-kit.com)
- [shadcn/ui Components](https://ui.shadcn.com)
- [React Markdown](https://github.com/remarkjs/react-markdown)
