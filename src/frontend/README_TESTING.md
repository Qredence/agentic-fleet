# Frontend Testing Guide

This guide covers the comprehensive testing setup for the AgenticFleet frontend application using Vitest, React Testing Library, and modern testing practices.

## 🧪 Testing Stack

**Testing Framework**: Vitest (fast, modern, Vite-native)
**Testing Library**: @testing-library/react (component testing)
**Environment**: jsdom (DOM simulation)
**Coverage**: v8 provider with HTML/JSON reports

## 📁 Test Structure

```
src/frontend/src/
├── components/
│   └── chat/
│       ├── ChatMessage.tsx
│       ├── ChatInput.tsx
│       └── __tests__/
│           ├── ChatMessage.test.tsx
│           └── ChatInput.test.tsx
├── lib/
│   └── __tests__/
│       └── api.test.ts
├── stores/
│   └── __tests__/
│       └── chatStore.test.ts
├── test/
│   └── setup.ts
└── vitest.config.ts
```

## 🚀 Quick Start

### Run All Frontend Tests

```bash
make test-frontend
```

### Run Tests in Watch Mode

```bash
cd src/frontend/src && npm run test:watch
```

### Run Tests with Coverage

```bash
cd src/frontend/src && npm run test:coverage
```

### Run Tests with UI

```bash
cd src/frontend/src && npm run test:ui
```

## 📝 Writing Tests

### Component Testing Example

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatMessage from '../ChatMessage';

describe('ChatMessage', () => {
  it('renders user message correctly', () => {
    render(<ChatMessage
      content="Hello!"
      role="user"
      timestamp={new Date()}
    />);

    expect(screen.getByText('Hello!')).toBeInTheDocument();
    expect(screen.getByText('User')).toBeInTheDocument();
  });
});
```

### API Testing Example

```typescript
import { describe, it, expect, beforeEach, vi } from "vitest";
import { chatApi } from "@/lib/api/chat";

// Mock fetch
global.fetch = vi.fn();

describe("Chat API", () => {
  it("sends message with correct format", async () => {
    const mockResponse = { content: "Response" };
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await chatApi.sendMessage({
      content: "Hello!",
      workflowId: "magentic_fleet",
    });

    expect(fetch).toHaveBeenCalledWith("/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: [{ role: "user", content: "Hello!" }],
        model: "magentic_fleet",
      }),
    });
  });
});
```

### Store Testing Example

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useChatStore } from "@/stores/chatStore";

describe("Chat Store", () => {
  it("adds message correctly", () => {
    const { result } = renderHook(() => useChatStore());

    act(() => {
      result.current.addMessage({
        id: "msg-1",
        content: "Hello!",
        role: "user",
        timestamp: new Date(),
      });
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe("Hello!");
  });
});
```

## 🛠️ Testing Utilities

### Mock API Responses

```typescript
// Setup mock responses
const mockApiResponse = {
  id: "response-1",
  content: "Hello back!",
  role: "assistant",
  timestamp: new Date().toISOString(),
};

fetch.mockResolvedValueOnce({
  ok: true,
  json: async () => mockApiResponse,
  status: 200,
});
```

### Mock Server-Sent Events

```typescript
// EventSource is automatically mocked in setup.ts
global.EventSource = vi.fn().mockImplementation(() => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  close: vi.fn(),
  readyState: 1,
}));
```

### User Interactions

```typescript
import { fireEvent, userEvent } from "@testing-library/user-event";

// Simple events
fireEvent.click(screen.getByRole("button"));

// Complex user interactions
const user = userEvent.setup();
await user.click(screen.getByRole("button"));
await user.type(screen.getByRole("textbox"), "Hello World");
```

## 📊 Coverage Configuration

### Coverage Thresholds

```json
{
  "thresholds": {
    "global": {
      "branches": 70,
      "functions": 70,
      "lines": 70,
      "statements": 70
    }
  }
}
```

### Excluded Files

- `node_modules/`
- `src/test/`
- `**/*.d.ts`
- `**/*.config.*`
- `dist/`
- `coverage/`

## 🔧 Configuration Files

### vitest.config.ts

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      thresholds: {
        global: {
          branches: 70,
          functions: 70,
          lines: 70,
          statements: 70,
        },
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

### src/test/setup.ts

```typescript
import "@testing-library/jest-dom";
import { beforeAll, afterEach, afterAll } from "vitest";

// Mock APIs and browser APIs
global.fetch = vi.fn();
global.EventSource = vi.fn().mockImplementation(() => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  close: vi.fn(),
}));

beforeAll(() => {
  console.log("🧪 Setting up test environment");
});

afterEach(() => {
  vi.clearAllMocks();
});

afterAll(() => {
  console.log("✅ Tests completed");
});
```

## 🎯 Testing Best Practices

### 1. Test User Behavior, Not Implementation

```typescript
// ✅ Good: Test what user sees
expect(screen.getByText("Loading...")).toBeInTheDocument();

// ❌ Bad: Test internal state
expect(component.state.isLoading).toBe(true);
```

### 2. Use Accessible Queries

```typescript
// ✅ Good: Use accessible selectors
screen.getByRole("button", { name: "Send message" });

// ❌ Bad: Use implementation details
screen.container.querySelector(".send-button");
```

### 3. Test Component Variations

````typescript
it('handles different message types', () => {
  // Test user messages
  render(<ChatMessage role="user" content="Hello" />);
  expect(screen.getByText('User')).toBeInTheDocument();

  // Test assistant messages
  render(<ChatMessage role="assistant" content="Hi there!" />);
  expect(screen.getByText('Assistant')).toBeInTheDocument();

  // Test code content
  render(<ChatMessage role="assistant" content="```console.log('test')```" />);
  expect(screen.getByText('console.log')).toBeInTheDocument();
});
````

### 4. Mock External Dependencies

```typescript
// Mock API calls
vi.mock("@/lib/api/chat", () => ({
  chatApi: {
    sendMessage: vi.fn().mockResolvedValue({ content: "Mock response" }),
  },
}));

// Mock stores
vi.mock("@/stores/chatStore", () => ({
  useChatStore: () => ({
    messages: [],
    addMessage: vi.fn(),
  }),
}));
```

### 5. Test Error Scenarios

```typescript
it('handles API errors gracefully', async () => {
  const { getByRole } = render(<ChatComponent />);

  // Mock API error
  fetch.mockRejectedValueOnce(new Error('Network error'));

  await userEvent.click(getByRole('button', { name: 'Send' }));

  expect(getByText('Failed to send message')).toBeInTheDocument();
});
```

## 📋 Available Scripts

| Command                 | Description                       |
| ----------------------- | --------------------------------- |
| `npm test`              | Run tests once                    |
| `npm run test:watch`    | Run tests in watch mode           |
| `npm run test:ui`       | Run tests with visual UI          |
| `npm run test:coverage` | Run tests with coverage           |
| `npm run test:run`      | Run tests without watch (CI mode) |

## 🔄 Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run Frontend Tests
  run: |
    cd src/frontend/src
    npm ci
    npm run test:run
    npm run test:coverage
```

### Coverage Reporting

Coverage reports are generated in:

- `coverage/index.html` - Interactive HTML report
- `coverage/coverage-final.json` - Machine-readable data
- Console output - Summary during test run

## 🐛 Common Issues & Solutions

### Import Path Issues

Ensure Vite aliases are properly configured:

```typescript
// vitest.config.ts
resolve: {
  alias: {
    '@': path.resolve(__dirname, './src'),
  },
}
```

### Mock Persistence

Clear mocks between tests:

```typescript
afterEach(() => {
  vi.clearAllMocks();
});
```

### Async Testing

Use `waitFor` for async operations:

```typescript
import { waitFor } from "@testing-library/react";

await waitFor(() => {
  expect(screen.getByText("Response loaded")).toBeInTheDocument();
});
```

## 📚 Additional Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
- [Jest DOM Matchers](https://github.com/testing-library/jest-dom)

## 🔍 Troubleshooting

### Tests Run Slow

- Check for unnecessary `waitFor` usage
- Optimize mock implementations
- Consider test isolation

### Coverage Low

- Check exclude patterns in config
- Ensure all components are tested
- Review threshold settings

### Mock Issues

- Verify mock setup in test files
- Check global mock configuration
- Ensure proper cleanup between tests
