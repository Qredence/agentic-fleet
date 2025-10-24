# shadcn/ui Primitives

**⚠️ DO NOT MODIFY THESE COMPONENTS DIRECTLY**

These components are managed by the shadcn/ui CLI and should not be manually edited.

## What's Here

This folder contains 45+ UI primitive components based on Radix UI:

- **Forms**: button, input, textarea, checkbox, radio-group, select, switch, slider
- **Layout**: card, separator, tabs, accordion, collapsible, sheet, dialog
- **Overlays**: tooltip, popover, dropdown-menu, context-menu, hover-card
- **Feedback**: alert, alert-dialog, badge, toast, sonner, skeleton, progress
- **Navigation**: breadcrumb, menubar, navigation-menu, pagination
- **Data**: table, calendar, form
- **Misc**: avatar, aspect-ratio, carousel, chart, resizable, scroll-area, sidebar, label

## Import Convention

**Always use individual imports** (NO barrel export to preserve tree-shaking):

```typescript
// Correct
import { Button } from "@/components/ui/shadcn/button";
import { Card } from "@/components/ui/shadcn/card";
import { Dialog } from "@/components/ui/shadcn/dialog";

// Incorrect (don't create barrel export)
import { Button, Card } from "@/components/ui/shadcn";
```

## Updating Components

To add or update shadcn/ui components, use the CLI:

```bash
npx shadcn@latest add button
npx shadcn@latest add dialog
```

## Customization

If you need to customize a component:

1. **DON'T modify files here**
2. Create a wrapper in `@/components/ui/custom/`
3. Compose the shadcn primitive with your custom logic

Example:

```typescript
// ui/custom/my-custom-button.tsx
import { Button } from '@/components/ui/shadcn/button';

export function MyCustomButton({ children, ...props }) {
  return <Button className="my-custom-styles" {...props}>{children}</Button>;
}
```

## Documentation

- shadcn/ui docs: https://ui.shadcn.com
- Radix UI docs: https://radix-ui.com
