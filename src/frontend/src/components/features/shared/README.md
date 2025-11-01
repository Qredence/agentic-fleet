# Shared Feature Components

Components shared across multiple features.

## Components

- **`ErrorBoundary.tsx`** - React error boundary for graceful error handling
- **`ConnectionStatusIndicator.tsx`** - Backend health status and connectivity UI

## Usage

```typescript
import { ErrorBoundary, ConnectionStatusIndicator } from '@/components/features/shared';

// Wrap your app or features
<ErrorBoundary>
  <YourApp />
</ErrorBoundary>

// Display connection status
<ConnectionStatusIndicator status={connectionStatus} />
```

## Purpose

Shared infrastructure components that support multiple features but don't belong to a specific domain.
