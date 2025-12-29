# Frontend Registries & Components Guide

This guide documents the component registries used in the AgenticFleet frontend and how to work with them.

## Available Registries

| Registry                | URL                         | Purpose                   | Component Count |
| ----------------------- | --------------------------- | ------------------------- | --------------- |
| **shadcn**              | https://ui.shadcn.com/r     | Basic UI primitives       | 100+            |
| **@ai-elements**        | https://registry.ai-sdk.dev | AI-specific components    | 77              |
| **@pureui**             | https://pure.kam-ui.com/r   | Alternative UI primitives | 291             |
| **@blocks**             | https://blocks.so/r         | Pre-built chat interfaces | 70              |
| **@openai/apps-sdk-ui** | NPM package                 | ChatGPT app components    | 50+             |

## Component Source Decision Tree

When adding a component, follow this decision tree:

```
Is it a basic UI primitive (button, input, dialog)?
├─ Check shadcn registry
│  ├─ Available? → npx shadcn add button
│  │               Goes to: components/ui/
│  └─ Not available? → Create in components/ui/
│
Is it AI-specific (chain-of-thought, artifact, canvas)?
├─ Check @ai-elements registry
│  ├─ Available and fits? → npx shadcn add @ai-elements/chain-of-thought
│  │                       Goes to: components/registry/ai-elements/
│  └─ Not available? → Create in features/[feature]/components/
│
Is it a pre-built chat interface?
├─ Check @blocks registry
│  ├─ Available? → npx shadcn add @blocks/ai-01
│  │               Goes to: components/registry/blocks/
│  └─ Not available? → Build custom in features/chat/
│
Is it OpenAI-specific (ChatGPT app components)?
└─ Check @openai/apps-sdk-ui
   ├─ Available? → Copy from node_modules/@openai/apps-sdk-ui
   │               Goes to: components/apps-sdk-ui/
   └─ Not available? → Build custom in features/[feature]/components/
```

## Registry Component Placement

### shadcn UI Primitives

```
components/ui/
├── button.tsx
├── input.tsx
├── dialog.tsx
└── index.ts
```

### @ai-elements

```
components/registry/ai-elements/
├── ChainOfThought.tsx      # → npx shadcn add @ai-elements/chain-of-thought
├── Artifact.tsx           # → npx shadcn add @ai-elements/artifact
└── index.ts
```

### @blocks

```
components/registry/blocks/
├── AI01.tsx             # → npx shadcn add @blocks/ai-01
└── index.ts
```

### @openai/apps-sdk-ui

```
components/apps-sdk-ui/
├── CodeBlock.tsx         # From node_modules/@openai/apps-sdk-ui
└── index.ts
```

## Common Commands

### List Available Components

```bash
# List all registries
npx shadcn list

# List specific registry
npx shadcn list @ai-elements
npx shadcn list @blocks
npx shadcn list @pureui
```

### View Component Before Adding

```bash
# Preview component code
npx shadcn view @ai-elements/chain-of-thought
npx shadcn view @blocks/ai-01
```

### Add Components

```bash
# Add shadcn UI primitive
npx shadcn add button

# Add AI component
npx shadcn add @ai-elements/chain-of-thought

# Add chat block
npx shadcn add @blocks/ai-01
```

### Check for Updates

```bash
# Check if component has updates
npx shadcn diff button
```

## shadcn MCP Server

The `.mcp.json` config enables the shadcn MCP server for AI-assisted development:

```json
{
  "mcpServers": {
    "shadcn": {
      "command": "npx",
      "args": ["shadcn@latest", "mcp"]
    }
  }
}
```

### MCP Capabilities

1. **Search registries**: Find components across all registries
2. **View component code**: Preview before adding
3. **Add components**: Directly install from registries
4. **Diff updates**: Check for component updates
5. **Project info**: Get current shadcn configuration

### Example MCP Workflows

When MCP tools are integrated:

```
Developer: "I need a chain of thought component"

1. AI searches registries
2. Presents options:
   - @ai-elements/chain-of-thought: AI-powered component
   - @blocks/chat-cot: Pre-built chat interface

3. Developer chooses: "Use @ai-elements"

4. AI executes: npx shadcn add @ai-elements/chain-of-thought

5. Component added to: components/registry/ai-elements/
```

## Registry Comparison Guidelines

### When to Use Registry vs. Custom

| Scenario            | Registry                       | Custom                       |
| ------------------- | ------------------------------ | ---------------------------- |
| Basic button/input  | ✅ `npx shadcn add button`     | ❌ Don't reinvent            |
| Chain-of-thought UI | ⚠️ Try `@ai-elements` first    | If doesn't fit, build custom |
| Chat interface      | ⚠️ Try `@blocks` for prototype | For production, build custom |
| Feature-specific    | ❌ Registry unlikely to have   | Build in `features/`         |
| ChatGPT-specific    | ✅ `@openai/apps-sdk-ui`       | N/A                          |

### Component Evaluation Checklist

Before using a registry component, consider:

- [ ] Does it match our design system (Tailwind v4, theme tokens)?
- [ ] Is it compatible with React 19?
- [ ] Does it support dark mode (our default)?
- [ ] Is the dependency footprint acceptable?
- [ ] Can we customize it easily (open code approach)?
- [ ] Is it actively maintained?

## Current Registry Usage

| Component           | Source | Location              | Notes                                        |
| ------------------- | ------ | --------------------- | -------------------------------------------- |
| All UI primitives   | shadcn | `components/ui/`      | Standard shadcn components                   |
| ChainOfThoughtTrace | Custom | `features/workflow/`  | Evaluate `@ai-elements` replacement          |
| CodeBlock           | Custom | `components/message/` | Evaluate `@openai/apps-sdk-ui` replacement   |
| Markdown            | Custom | `components/message/` | Evaluate `@ai-elements/markdown` replacement |

## Migration Decisions

### Decisions Made

1. **Keep custom ChainOfThoughtTrace**:
   - Custom implementation has specific backend event mapping
   - `@ai-elements/chain-of-thought` may not integrate seamlessly

2. **Keep custom CodeBlock**:
   - Tightly integrated with Shiki syntax highlighting
   - Specific streaming behavior for AI responses

3. **Keep custom Markdown**:
   - Uses streamdown for AI-optimized markdown rendering
   - Custom remark plugins for GFM, code highlighting

### Future Evaluations

When adding new features:

- Check `@ai-elements` for AI-specific components
- Check `@blocks` for rapid prototyping
- Prefer shadcn for basic UI primitives

## Adding Custom Components

When building custom components:

1. Follow the file placement decision tree above
2. Use existing design tokens from `styles/variables-*.css`
3. Reuse shadcn primitives where possible
4. Follow React 19 conventions (no `forwardRef` unless needed)
5. Keep components open and customizable (shadcn philosophy)

## References

- [shadcn Docs](https://ui.shadcn.com/docs)
- [shadcn Components](https://ui.shadcn.com/docs/components)
- [AI Elements Registry](https://registry.ai-sdk.dev)
- [Pure UI](https://pure.kam-ui.com)
- [Blocks](https://blocks.so)
- [OpenAI Apps SDK UI](https://github.com/openai/apps-sdk-ui)
