---
name: AgenticFleet Frontend Component Workflow
description: End-to-end guide for creating React components in AgenticFleet's frontend, from design tokens through Tailwind styling, shadcn/ui integration, state management, to testing.
---

# Frontend Component Workflow

Use this skill when creating or modifying React components in AgenticFleet's frontend (`src/frontend/src/`).

## When to Use

- Creating new UI components (chat, workflow, dashboard)
- Adding shadcn/ui primitives
- Integrating components with Zustand stores or React Query
- Writing component tests with Vitest

## Project Structure

```
src/frontend/src/
├── components/           # Reusable UI components
│   ├── ui/              # shadcn/ui primitives (Button, Dialog, etc.)
│   ├── chat/            # Chat domain (PromptInput, ChatMessages)
│   ├── message/         # Message rendering (Markdown, Reasoning)
│   ├── workflow/        # Workflow visualization
│   └── layout/          # App structure (headers, sidebars)
├── pages/               # Page-level views (composition layer)
├── stores/              # Zustand stores (client state)
├── api/                 # HTTP client, SSE, React Query hooks
├── hooks/               # Custom React hooks
├── styles/              # Tailwind v4 + design tokens
│   ├── variables-primitive.css    # Base tokens (colors, spacing)
│   ├── variables-semantic.css     # Semantic tokens (--color-primary)
│   ├── variables-components.css   # Component tokens
│   ├── theme.css                  # Theme configuration
│   ├── animations.css             # Animation utilities
│   └── utilities.css              # Custom utility classes
└── tests/               # Vitest + React Testing Library
```

## Step 1: Design Tokens & Styling

### Token Hierarchy

1. **Primitive tokens** (`variables-primitive.css`): Raw values

   ```css
   --color-blue-500: #3b82f6;
   --spacing-4: 1rem;
   ```

2. **Semantic tokens** (`variables-semantic.css`): Context-aware

   ```css
   --color-primary: var(--color-blue-500);
   --color-background: var(--color-gray-950);
   ```

3. **Component tokens** (`variables-components.css`): Component-specific
   ```css
   --button-bg: var(--color-primary);
   --card-border-radius: var(--radius-lg);
   ```

### Tailwind v4 Usage

Use Tailwind classes with semantic tokens:

```tsx
<div className="bg-background text-foreground border-border" />
```

Custom utilities in `utilities.css`:

```tsx
<div className="glass-bar" /> // Frosted glass effect
```

## Step 2: shadcn/ui Primitives

### Location

All shadcn/ui components live in `components/ui/`.

### Adding New Primitives

```bash
cd src/frontend
npx shadcn add <component-name>
```

### Import Pattern

```tsx
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
```

### Customization

Extend via className, never modify `components/ui/` directly:

```tsx
<Button className="rounded-full px-6" variant="outline">
  Custom Button
</Button>
```

## Step 3: Domain Component Creation

### File Structure

```
components/chat/
├── index.ts              # Barrel exports
├── prompt-input.tsx      # Main component
├── chat-messages.tsx     # Related component
└── types.ts              # Shared types (optional)
```

### Component Pattern

```tsx
import { cn } from "@/lib/utils";

export type MyComponentProps = {
  isLoading?: boolean;
  className?: string;
  children: React.ReactNode;
} & React.ComponentProps<"div">;

export function MyComponent({
  isLoading = false,
  className,
  children,
  ...props
}: MyComponentProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-4",
        isLoading && "opacity-60",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
```

### Compound Components

For complex components, use compound pattern:

```tsx
function MyComponent({ children }: { children: React.ReactNode }) {
  return <div>{children}</div>;
}

function MyComponentHeader({ children }: { children: React.ReactNode }) {
  return <header>{children}</header>;
}

export { MyComponent, MyComponentHeader };
```

### Animation

Use `motion/react` (NOT framer-motion):

```tsx
import { motion } from "motion/react";

<motion.div
  initial={{ opacity: 0, y: 10 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.2 }}
>
  Animated content
</motion.div>;
```

## Step 4: State Integration

### Zustand Store Pattern

```tsx
import { create } from "zustand";
import { devtools } from "zustand/middleware";

interface MyState {
  // Data
  items: Item[];
  isLoading: boolean;

  // Actions
  fetchItems: () => Promise<void>;
  addItem: (item: Item) => void;
}

const storeImpl = (set, get): MyState => ({
  items: [],
  isLoading: false,

  fetchItems: async () => {
    set({ isLoading: true });
    try {
      const items = await api.getItems();
      set({ items, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
    }
  },

  addItem: (item) => {
    set((state) => ({ items: [...state.items, item] }));
  },
});

// Wrap with devtools only in development
export const useMyStore = create<MyState>()(
  import.meta.env.DEV ? devtools(storeImpl, { name: "my-store" }) : storeImpl,
);
```

### Using Store in Components

```tsx
import { useChatStore } from "@/stores/chatStore";

function MyComponent() {
  const { messages, isLoading, sendMessage } = useChatStore();
  // ...
}
```

### React Query for Server State

```tsx
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";

function MyComponent() {
  const { data, isLoading } = useQuery({
    queryKey: ["items"],
    queryFn: () => api.getItems(),
  });

  const mutation = useMutation({
    mutationFn: api.createItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["items"] });
    },
  });
}
```

### State Separation

- **Server state**: React Query (data from API)
- **Client state**: Zustand (UI preferences, local state)
- **Component state**: useState (ephemeral, component-scoped)

## Step 5: Testing with Vitest

### Test File Location

```
src/tests/
├── components/
│   └── my-component.test.tsx
└── setup.ts
```

### Test Pattern

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MyComponent } from "@/components/chat/my-component";

describe("MyComponent", () => {
  it("renders children", () => {
    render(<MyComponent>Hello</MyComponent>);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("applies loading state", () => {
    render(<MyComponent isLoading>Content</MyComponent>);
    expect(screen.getByText("Content").parentElement).toHaveClass("opacity-60");
  });

  it("handles click events", async () => {
    const onClick = vi.fn();
    render(<MyComponent onClick={onClick}>Click me</MyComponent>);
    fireEvent.click(screen.getByText("Click me"));
    expect(onClick).toHaveBeenCalled();
  });
});
```

### Running Tests

```bash
make test-frontend          # Run all tests
cd src/frontend && npm run test:ui   # Interactive UI
cd src/frontend && npm run test:watch  # Watch mode
```

## Import Conventions

### Path Aliases

```tsx
import { Button } from "@/components/ui/button"; // components/ui
import { useChatStore } from "@/stores/chatStore"; // stores
import { api } from "@/api/client"; // api
import { cn } from "@/lib/utils"; // utilities
import { useIsMobile } from "@/hooks/use-mobile"; // hooks
```

### Barrel Exports

Each domain folder should have `index.ts`:

```tsx
// components/chat/index.ts
export * from "./prompt-input";
export * from "./chat-messages";
```

Then import as:

```tsx
import { PromptInput, ChatMessages } from "@/components/chat";
```

## Checklist for New Components

- [ ] Created in appropriate directory (`components/ui/`, `components/chat/`, etc.)
- [ ] Uses TypeScript with proper prop types
- [ ] Uses `cn()` for className merging
- [ ] Forwards refs if wrapping DOM elements
- [ ] Uses semantic Tailwind tokens (not hardcoded colors)
- [ ] Animations use `motion/react`
- [ ] Added to barrel export (`index.ts`)
- [ ] Tests written in `src/tests/`
- [ ] Works in both light and dark themes
