# Frontend Testing Guide

## Overview

The frontend uses **Vitest + Testing Library** for fast unit-style tests under `src/tests/`. All tests run in `jsdom` with `fetch` globally mocked in `src/tests/setup.ts` to keep the test suite fast and deterministic.

## Test Commands

From `src/frontend` directory:

```bash
# Run all tests (default)
npm run test

# Run tests once without watch mode (CI)
npm run test:run

# Watch mode with UI
npm run test:ui

# Watch mode (headless)
npm run test:watch

# Run tests with coverage report
npm run test:coverage
```

See `package.json` for the full command list.

## Test Configuration

### Environment Variables

Tests use `VITE_API_URL` environment variable, but most tests mock the API calls via global `fetch` mock in `src/tests/setup.ts`. The mock handles endpoints:

- `GET /api/health` - Health check
- `POST /conversations` - Create conversation
- `GET /api/conversations/:id` - Get conversation
- `POST /api/chat` - Send chat message

### Timeouts

Test timeouts are configured in `vitest.config.ts`:

- **Global timeout**: 15 seconds
- **Hook timeout**: 15 seconds

## Available Test Scripts

From package.json:

```bash
# Development
npm run test          # Run tests in watch mode
npm run test:watch    # Run tests in watch mode (alternative)
npm run test:ui      # Interactive UI mode

# CI/Production
npm run test:run     # Run once without watch mode
npm run test:coverage # Run coverage report

# Linting & Formatting
npm run lint          # Run ESLint
npm run format        # Run Prettier formatting
```

## Test Structure

### Component Tests (`src/tests/`)

Tests are organized by component domain:

```
src/tests/
├── api/                    # API client tests
│   └── client.optimization.test.ts
├── components/
│   └── prompt-kit/         # Chain of Thought tests
│       └── chain-of-thought.test.tsx
├── dashboard/              # Dashboard component tests
│   └── OptimizationDashboard.test.tsx
├── utils/                  # Shared test utilities
│   ├── render.ts
│   ├── factories.ts
│   └── queries.ts
└── App.test.tsx           # Main app tests
```

### Test Utilities

- **`src/tests/setup.ts`** - Global test setup with fetch mocking
- **`@testing-library/react`** - UI testing utilities
- **`@testing-library/user-event`** - User interaction simulation
- **`nanoid`** - For generating unique IDs in mock data

## Writing Component Tests

### Basic Pattern

```typescript
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { YourComponent } from "@/components/path";

// Mock external dependencies
vi.mock("@/stores", () => ({
  useChatStore: () => ({
    messages: [],
    sendMessage: vi.fn(),
  }),
}));

describe("YourComponent", () => {
  it("renders correctly", () => {
    render(<YourComponent />);
    expect(screen.getByText("Expected Text")).toBeInTheDocument();
  });

  it("handles user interactions", async () => {
    const user = userEvent.setup();
    const mockSend = vi.fn();
    vi.mocked(useChatStore).mockReturnValue({ sendMessage: mockSend });

    render(<YourComponent />);
    await user.click(screen.getByRole("button"));
    expect(mockSend).toHaveBeenCalled();
  });
});
```

### React Query Mock Pattern

When testing components using React Query hooks:

```typescript
// 1. Create mutable mock state
let mockData: YourHookReturnType = {
  data: undefined,
  isLoading: false,
  isError: false,
};

// 2. Mock the hook with access to mutable state
vi.mock("@/api/hooks", () => ({
  useYourHook: () => mockData,
  // Add other hooks as needed
}));

// 3. Reset mock state before each test
beforeEach(() => {
  mockData = {
    data: undefined,
    isLoading: false,
    isError: false,
  };
});

// 4. Update mock state to test different scenarios
it("shows loading state", () => {
  mockData.isLoading = true;
  render(<YourComponent />);
  expect(screen.getByText(/loading/i)).toBeInTheDocument();
});
```

## Mock Data Patterns

### Conversation Factory

```typescript
import { Conversation } from "@/api/types";
import { faker } from "@faker-js/faker";

export function createMockConversation(
  overrides?: Partial<Conversation>,
): Conversation {
  return {
    id: faker.string.uuid(),
    title: faker.lorem.words(3),
    created_at: Date.now(),
    messages: [],
    ...overrides,
  };
}
```

### Message Factory

```typescript
import { Message } from "@/api/types";
import { faker } from "@faker-js/faker";

export function createMockMessage(overrides?: Partial<Message>): Message {
  return {
    id: faker.string.uuid(),
    role: faker.helpers.arrayElement(["user", "assistant"]),
    content: faker.lorem.paragraph(),
    created_at: Date.now(),
    ...overrides,
  };
}
```

## Best Practices

### Testing React Components

1. **Test user-facing behavior**: Prefer queries like `getByRole`, `getByText`, `getByLabelText` over implementation details
2. **Use `userEvent` for interactions**: Simulate real user interactions instead of `fireEvent`
3. **Mock external dependencies**: Mock API calls, stores, and contexts for isolation
4. **Keep tests focused**: Each test should verify one specific behavior

### Testing React Query Hooks

1. **Mock with mutable state**: Use mutable mock objects to test different states
2. **Test loading/error states**: Verify UI responds correctly to async states
3. **Test mutations**: Verify side effects and cache updates

### Performance Tips

1. **Use `vi.mock()` at module level**: Mock heavy dependencies at the top of test files
2. **Mock expensive operations**: Mock API calls, localStorage, timers
3. **Use `beforeEach` for setup**: Reset mocks and state between tests
4. **Avoid complex arrangements**: Keep test setup simple and focused

## Troubleshooting

### Tests Failing with Fetch Errors

**Cause**: Unmocked fetch calls in tests.

**Solution**:

1. Check `src/tests/setup.ts` has mock for your endpoint
2. Add new endpoint mock if needed
3. Or use `vi.spyOn(globalThis, "fetch")` in specific test

### React Query State Not Updating

**Cause**: Mock not returning updated state.

**Solution**:
Use mutable mock pattern shown above, updating mock state before rendering.

### Component Not Rendering

**Cause**: Missing provider or context.

**Solution**:
Wrap component with necessary providers:

```typescript
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SidebarProvider } from "@/components/ui/sidebar";

const queryClient = new QueryClient();

render(
  <QueryClientProvider client={queryClient}>
    <SidebarProvider>
      <YourComponent />
    </SidebarProvider>
  </QueryClientProvider>
);
```

### TypeScript Errors in Mocks

**Cause**: Incorrect mock typing.

**Solution**:
Use TypeScript casting or utility types:

```typescript
vi.mocked(useChatStore).mockReturnValue(mockStore as any);
// or
vi.mock("@/stores", () => ({
  useChatStore: vi.fn(() => mockStore),
}));
```

## Coverage Thresholds

Coverage thresholds are configured in `vitest.config.ts`:

```typescript
coverage: {
  thresholds: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },
}
```

Run `npm run test:coverage` to generate coverage report.

## Test Configuration

### Environment Variables

Tests use the following environment variables (primarily for app runtime; most tests mock `fetch`):

- `VITE_API_URL`: Backend API origin (default: `http://localhost:8000`; the frontend appends `/api` automatically)

You can override in `.env.test`:

```bash
VITE_API_URL=http://localhost:8080
```

### Timeouts

Test timeouts are configured based on test type:

- **Unit tests**: 5 seconds (default)
- **Integration tests**: 15 seconds (to accommodate real API calls)

## Test Types

### Unit Tests

Unit tests use mocked dependencies and run in isolation:

```typescript
import { describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useChatController } from "./useChatController";

// Mock the API client
vi.mock("./useChatClient", () => ({
  getHealth: vi.fn(() => Promise.resolve({ status: "ok" })),
  createConversation: vi.fn(() =>
    Promise.resolve({ id: "test-id", title: "Test", messages: [] }),
  ),
}));

describe("useChatController - Unit Tests", () => {
  it("initializes with default state", () => {
    const { result } = renderHook(() => useChatController());

    expect(result.current.messages).toEqual([]);
    expect(result.current.pending).toBe(false);
  });
});
```

### Integration Tests

Integration tests make real API calls and require a running backend:

```typescript
import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useChatController } from "./useChatController";

// Integration tests - no mocks, real backend required
describe("useChatController - Integration Tests", () => {
  it("sends chat messages and updates state with response", async () => {
    const { result } = renderHook(() => useChatController());

    await waitFor(() => expect(result.current.conversationId).not.toBeNull(), {
      timeout: 5000,
    });

    await act(async () => {
      await result.current.send("Hello from integration test");
    });

    expect(result.current.messages.length).toBeGreaterThan(0);
  });
});
```

## Writing Tests

### Unit Test Guidelines

1. **Mock external dependencies**: Use `vi.mock()` to mock API clients and external services
2. **Test in isolation**: Focus on component/hook logic without network calls
3. **Fast execution**: Unit tests should complete in milliseconds
4. Prefer asserting **user-visible behavior** (roles/labels) over implementation details

Example:

```typescript
vi.mock("./useChatClient", () => ({
  getHealth: vi.fn(() => Promise.resolve({ status: "ok" })),
  sendChat: vi.fn((conversationId, message) =>
    Promise.resolve({
      conversation_id: conversationId,
      message: { role: "assistant", content: "Mocked response" },
      messages: [],
    }),
  ),
}));

describe("ChatComponent - Unit Tests", () => {
  it("displays loading state while sending message", async () => {
    // Test component behavior with mocked API
  });
});
```

## Troubleshooting

### Unit Tests

#### Tests Failing with Module Errors

**Cause**: Missing or incorrect mocks.

**Solution**:

```typescript
// Ensure all external modules are mocked
vi.mock("./useChatClient", () => ({
  getHealth: vi.fn(),
  createConversation: vi.fn(),
  sendChat: vi.fn(),
}));
```

#### Mock Not Working

**Cause**: Mock defined after import or in wrong scope.

**Solution**: Define mocks at the top of the file, before imports that use them.

### Integration Tests

### Tests Failing with Network Errors

**Cause**: Backend is not running.

**Solution**:

```bash
# Start backend first
make backend

# Then run tests
cd src/frontend && npm run test:run
```

### Tests Timing Out

**Cause**: Backend is slow to respond or not accessible.

**Solution**:

1. Check backend is running: `curl http://localhost:8000/v1/health`
2. Increase timeouts in `vitest.config.ts` if needed
3. Check backend logs for errors

### Connection Refused Errors

**Cause**: Wrong API URL or backend not listening.

**Solution**:

1. Verify backend port: Check `.env` in project root
2. Update `VITE_API_URL` in `src/frontend/.env.test`
3. Ensure no firewall blocking localhost:8000

## CI/CD Integration

### Recommended CI Pipeline Structure

Use separate jobs for unit and integration tests to optimize CI speed and reliability:

```yaml
jobs:
  frontend-unit-tests:
    name: Frontend Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20.x"
          cache: "npm"
          cache-dependency-path: "src/frontend/package-lock.json"

      - name: Install dependencies
        working-directory: src/frontend
        run: npm ci

      - name: Run unit tests
        working-directory: src/frontend
        run: npm run test:unit

      - name: Run linting
        working-directory: src/frontend
        run: npm run lint

  frontend-integration-tests:
    name: Frontend Integration Tests
    runs-on: ubuntu-latest
    needs: [backend-build] # Ensure backend is ready
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20.x"
          cache: "npm"
          cache-dependency-path: "src/frontend/package-lock.json"

      - name: Install dependencies
        working-directory: src/frontend
        run: npm ci

      - name: Start Backend
        run: make backend &

      - name: Wait for Backend
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:8000/v1/health; do sleep 2; done'

      - name: Run integration tests
        working-directory: src/frontend
        run: npm run test:integration
```

### Benefits of Separate Jobs

1. **Fast Feedback**: Unit tests run quickly without waiting for backend
2. **Parallel Execution**: Both test suites can run simultaneously
3. **Clear Failures**: Easy to identify if failure is in unit logic or integration
4. **Resource Efficiency**: Backend only starts when needed
5. **Flexible CI**: Can make integration tests optional or scheduled

## Best Practices

### General

1. **Start with unit tests**: Write unit tests first for fast feedback
2. **Add integration tests for critical paths**: Cover key user workflows with integration tests
3. **Mock external dependencies**: Use mocks in unit tests for speed and reliability
4. **Test both success and error cases**: Verify error handling in both test types

### Unit Tests

1. **Keep them fast**: Each test should complete in milliseconds
2. **Avoid real I/O**: Mock all network calls, file system access, etc.
3. **Test one thing**: Each test should verify a single behavior
4. **Use descriptive names**: Clearly describe what's being tested

### Integration Tests

1. **Test real workflows**: Verify complete user journeys
2. **Use real data**: Tests create actual conversations and messages
3. **Generous timeouts**: Allow adequate time for real API calls
4. **Handle flakiness**: Retry logic or longer waits for async operations
5. **Backend cleanup**: Ensure backend handles cleanup between test runs

## Future Enhancements

Potential improvements:

### Unit Testing

- Expand unit test coverage for all components and hooks
- Add snapshot testing for UI components
- Mock React Query for data fetching tests

### Integration Testing

- Test database seeding for predictable state
- Parallel test execution with isolated backend instances
- Performance benchmarking of critical paths
- Visual regression testing with Playwright

### CI/CD

- Separate unit and integration test jobs (recommended)
- Make integration tests opt-in or scheduled
- Add test result reporting and trends
- Automated flaky test detection
