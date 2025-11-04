# Frontend Testing Guide

## Overview

The frontend tests are **integration tests** that connect to the real backend API. This ensures tests verify actual API behavior rather than mocked responses.

## Prerequisites

**IMPORTANT**: The backend server must be running before executing tests.

### Start the Backend

From the project root:

```bash
# Option 1: Start full stack
make dev

# Option 2: Start backend only
make backend
```

The backend should be available at `http://localhost:8000`.

## Running Tests

### All Tests

```bash
cd src/frontend
npm run test
```

### Run Once (CI Mode)

```bash
npm run test:run
```

### Watch Mode

```bash
npm run test:watch
```

### With Coverage

```bash
npm run test:coverage
```

### UI Mode

```bash
npm run test:ui
```

## Test Configuration

### Environment Variables

Tests use the following environment variables:

- `VITE_API_URL`: Backend API URL (default: `http://localhost:8000`)

You can override in `.env.test`:

```bash
VITE_API_URL=http://localhost:8080
```

### Timeouts

Integration tests have increased timeouts to accommodate real API calls:

- Test timeout: 15 seconds
- Hook timeout: 15 seconds

## Test Types

### Integration Tests

All current tests are integration tests that:

- Make real HTTP requests to the backend
- Test actual API responses
- Verify end-to-end functionality
- Require backend to be running

### Example

```typescript
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
```

## Troubleshooting

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

For CI pipelines, ensure:

1. Backend starts before frontend tests
2. Health check passes before running tests
3. Proper cleanup after test runs

Example GitHub Actions:

```yaml
- name: Start Backend
  run: make backend &

- name: Wait for Backend
  run: |
    timeout 60 bash -c 'until curl -f http://localhost:8000/v1/health; do sleep 2; done'

- name: Run Frontend Tests
  run: |
    cd src/frontend
    npm run test:run
```

## Best Practices

1. **Always start backend first** - Tests will fail without it
2. **Use real data** - Tests create actual conversations and messages
3. **Clean up** - Backend should handle cleanup between test runs
4. **Timeouts** - Be generous with timeouts for real API calls
5. **Error handling** - Tests should verify both success and error cases

## Future Enhancements

Potential improvements:

- Add unit tests with mocks for faster CI
- Test database seeding for predictable state
- Parallel test execution with isolated backends
- Performance benchmarking
