# Custom UI Components

Application-specific UI components that build upon shadcn primitives.

## Components

- **`message.tsx`** - Composite message container with avatar, content, actions
- **`prompt-suggestion.tsx`** - Clickable prompt suggestion chips
- **`prompt-input/`** - Advanced prompt input with compound component pattern
- **`text-shimmer.tsx`** - Animated text shimmer effect
- **`code-block.tsx`** - Code syntax highlighting display
- **`markdown.tsx`** - Markdown rendering component
- **`theme-switch-button.tsx`** - Theme toggle button
- **`theme-switch-demo.tsx`** - Theme switcher demonstration

## Import Convention

```typescript
// Direct imports
import { Message } from '@/components/ui/custom/message';
import { PromptSuggestion } from '@/components/ui/custom/prompt-suggestion';

// Compound components
import { PromptInput } from '@/components/ui/custom/prompt-input';
<PromptInput.Root>
  <PromptInput.Textarea />
  <PromptInput.Actions />
</PromptInput.Root>
```

## Purpose

Custom UI components that:

- Build upon shadcn/ui primitives
- Add application-specific styling or behavior
- Provide reusable UI patterns unique to AgenticFleet
- Safe to modify and customize

## Guidelines

1. **Composition over modification**: Compose shadcn primitives rather than modifying them
2. **Reusability**: If used in 2+ places, it belongs here
3. **Domain-agnostic**: Keep feature-specific logic in `@/components/features`
4. **TypeScript strict mode**: All components must have proper types

## vs shadcn Components

| shadcn/ui            | custom          |
| -------------------- | --------------- |
| Framework primitives | App-specific UI |
| Managed by CLI       | Managed by team |
| Don't modify         | Safe to modify  |
| Generic/composable   | Domain-aware    |
