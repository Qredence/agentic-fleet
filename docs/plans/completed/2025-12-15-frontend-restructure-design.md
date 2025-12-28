# Frontend Restructure Design

**Date**: 2025-12-15
**Status**: Approved
**Goal**: Reorganize frontend to feature-based structure for clarity and performance optimization readiness

## Problem Statement

1. **Unclear file placement** - Developers unsure where new files should go
2. **Performance issues** - 880KB main bundle, no code splitting
3. **Inconsistent structure** - `blocks/` vs `prompt-kit/` distinction unclear
4. **Duplicate folders** - Both `test/` and `tests/` exist

## Solution: Feature-Based Structure

### Directory Structure

```
src/
├── app/                           # App shell
│   ├── App.tsx
│   ├── main.tsx
│   ├── index.css
│   └── providers/
│       └── AppProviders.tsx
│
├── features/                      # Domain-specific code
│   ├── chat/
│   │   ├── components/
│   │   │   ├── ChatContainer.tsx
│   │   │   ├── ChatHeader.tsx
│   │   │   ├── ChatMessages.tsx
│   │   │   ├── ChatSidebar.tsx
│   │   │   ├── ChainOfThought.tsx
│   │   │   ├── CodeBlock.tsx
│   │   │   ├── Markdown.tsx
│   │   │   ├── PromptInput/
│   │   │   └── index.ts
│   │   ├── hooks/
│   │   ├── stores/
│   │   │   └── chatStore.ts
│   │   ├── types/
│   │   └── index.ts
│   └── dashboard/
│       ├── components/
│       │   └── OptimizationDashboard.tsx
│       └── index.ts
│
├── shared/                        # Reusable code
│   ├── components/ui/             # shadcn primitives
│   ├── hooks/
│   │   ├── useTheme.ts
│   │   ├── useMobile.ts
│   │   └── index.ts
│   ├── lib/
│   │   ├── utils.ts
│   │   ├── codeDetection.ts
│   │   └── index.ts
│   └── contexts/
│       ├── ThemeContext.tsx
│       └── index.ts
│
├── api/                           # API layer (unchanged)
│   ├── client.ts
│   ├── config.ts
│   ├── hooks.ts
│   ├── http.ts
│   ├── sse.ts
│   ├── websocket.ts
│   ├── types.ts
│   └── index.ts
│
└── tests/                         # Test files (mirrors src/)
    ├── features/
    ├── shared/
    ├── api/
    └── utils/
```

### File Placement Decision Tree

When adding a new file:

1. **Is it specific to one feature?** → `features/<feature-name>/`
2. **Is it reusable UI (shadcn)?** → `shared/components/ui/`
3. **Is it a shared hook/util?** → `shared/hooks/` or `shared/lib/`
4. **Is it API-related?** → `api/`
5. **Is it app-level setup?** → `app/`

### Import Rules

- **Within feature**: Relative imports (`./components/ChatHeader`)
- **Cross-feature**: Import from feature index (`@/features/dashboard`)
- **Shared code**: Import from shared (`@/shared/components/ui`)

### Feature Index Files (Public API)

Each feature exports only what other features need:

```typescript
// features/chat/index.ts
export { ChatContainer } from "./components/ChatContainer";
export { useChatStore } from "./stores/chatStore";
export type { Message, Conversation } from "./types";
```

## Migration Plan

### File Moves

| Current Location                               | New Location                                 |
| ---------------------------------------------- | -------------------------------------------- |
| `components/blocks/full-chat-app.tsx`          | `features/chat/components/ChatContainer.tsx` |
| `components/prompt-kit/*`                      | `features/chat/components/`                  |
| `components/blocks/optimization-dashboard.tsx` | `features/dashboard/components/`             |
| `components/ui/*`                              | `shared/components/ui/`                      |
| `stores/chatStore.ts`                          | `features/chat/stores/`                      |
| `stores/index.ts`                              | `features/chat/stores/` (or remove)          |
| `hooks/useTheme.ts`                            | `shared/hooks/`                              |
| `hooks/use-mobile.ts`                          | `shared/hooks/useMobile.ts`                  |
| `lib/*`                                        | `shared/lib/`                                |
| `contexts/*`                                   | `shared/contexts/`                           |
| `App.tsx`                                      | `app/App.tsx`                                |
| `main.tsx`                                     | `app/main.tsx`                               |
| `index.css`                                    | `app/index.css`                              |

### Files to Delete

- `src/test/` (duplicate folder - consolidate into `tests/`)
- `src/styles/` (move contents to `app/` or delete if unused)
- `src/assets/` (move to `public/` if static, or `shared/assets/` if imported)

### Barrel Exports to Add

Each folder needs an `index.ts`:

- `shared/components/ui/index.ts`
- `shared/hooks/index.ts`
- `shared/lib/index.ts`
- `shared/contexts/index.ts`
- `features/chat/index.ts`
- `features/chat/components/index.ts`
- `features/dashboard/index.ts`

## Path Alias Updates

Update `vite.config.ts`:

```typescript
resolve: {
  alias: {
    "@": path.resolve(__dirname, "./src"),
    "@features": path.resolve(__dirname, "./src/features"),
    "@shared": path.resolve(__dirname, "./src/shared"),
    "@api": path.resolve(__dirname, "./src/api"),
    "@app": path.resolve(__dirname, "./src/app"),
  },
},
```

Update `tsconfig.json` paths accordingly.

## Benefits

1. **Clear file placement** - Decision tree eliminates confusion
2. **Code splitting ready** - Each feature can be lazy-loaded
3. **Scalable** - New features get their own folder
4. **Maintainable** - Related code stays together
5. **Testable** - Tests mirror source structure

## Next Steps (Performance)

After restructuring, address performance:

1. Lazy load `features/dashboard/` with `React.lazy()`
2. Configure Shiki to load only common languages
3. Add manual chunks in Vite for vendor splitting
4. Consider moving heavy deps (shiki, react-markdown) to dynamic imports
