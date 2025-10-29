# Chat Feature Components

Core chat interaction components for the AgenticFleet frontend.

## Components

- **`ChatContainer.tsx`** - Main orchestrator component managing chat state, SSE connection, messages, and approvals
- **`ChatMessage.tsx`** - Individual message rendering with streaming, tools, reasoning display
- **`ChatInput.tsx`** - User input form wrapper for prompt entry
- **`ChatHeader.tsx`** - Top navigation with model selector, conversation history, theme switcher
- **`ChatSidebar.tsx`** - Conversation history management and navigation

## Usage

```
import { ChatContainer } from '@/components/features/chat';

// The ChatContainer orchestrates all chat sub-components
<ChatContainer />
```

## Component Hierarchy

```
ChatContainer (orchestrator)
├── ChatHeader
│   └── ChatSidebar (via Sheet)
├── ChatMessage[] (message list)
├── ChatInput
└── ApprovalPrompt (when approval needed)
```

## Dependencies

- **UI**: `@/components/ui/shadcn` (Button, Card, Badge, etc.)
- **AI**: `@/components/ai` (Plan, Reasoning, Tool, Steps, ResponseStream)
- **Custom UI**: `@/components/ui/custom` (Message, PromptInput, etc.)
- **Hooks**: `@/lib/hooks` (useSSEConnection, useMessageState, etc.)

> **Convention:** shadcn primitives must be imported directly from `@/components/ui/shadcn/<component>`.
> Avoid using root-level aliases such as `@/components/ui/<component>` to ensure Vite can resolve the filesystem path consistently across platforms.
