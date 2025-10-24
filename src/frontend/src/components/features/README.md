# Features Components

This folder contains feature-specific components organized by domain.

## Structure

- **`chat/`** - Chat interaction feature (messages, input, header, sidebar, container)
- **`approval/`** - Human-in-the-loop approval workflow components
- **`shared/`** - Shared feature components (error boundaries, connection status)

## Import Convention

Use barrel exports for cleaner imports:

```typescript
// Preferred
import { ChatContainer, ChatMessage } from "@/components/features/chat";
import { ApprovalPrompt } from "@/components/features/approval";
import { ErrorBoundary } from "@/components/features/shared";

// Also acceptable (direct imports)
import { ChatContainer } from "@/components/features/chat/ChatContainer";
```

## Ownership

- **Owner**: Frontend team
- **Modification**: Safe to modify - these are application-specific components
- **Testing**: Changes should include component tests when adding new features

## Guidelines

1. Keep feature components focused on business logic
2. Delegate UI primitives to `@/components/ui/shadcn` or `@/components/ui/custom`
3. Extract reusable logic into hooks in `@/lib/hooks`
4. Use TypeScript strict mode for all new components
