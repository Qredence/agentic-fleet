# Approval Feature Components

Human-in-the-loop (HITL) approval workflow components.

## Components

- **`ApprovalPrompt.tsx`** - Approval card with code editing, approve/reject/modify actions

## Usage

```typescript
import { ApprovalPrompt } from '@/components/features/approval';

<ApprovalPrompt
  approval={approvalRequest}
  onApprove={handleApprove}
  onReject={handleReject}
  onModify={handleModify}
/>
```

## Purpose

Handles sensitive operations requiring human approval:

- Code execution
- File system operations
- External API calls
- Data modifications

## Dependencies

- **UI**: `@/components/ui/shadcn` (Button, Card, Badge, Textarea, etc.)
- **API**: `@/lib/api-client` (approval decision endpoints)
