import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useChatController } from "./useChatController";

// Integration tests using real backend API
// Ensure backend is running at http://localhost:8000 before running these tests

describe("useChatController - Integration Tests", () => {
  beforeEach(() => {
    // No mocks - using real API
  });

  it("initialises health and conversation state on mount", async () => {
    const { result } = renderHook(() => useChatController());

    await waitFor(
      () => {
        expect(result.current.health).toBe("ok");
        expect(result.current.conversationId).not.toBeNull();
      },
      { timeout: 5000 },
    );

    expect(result.current.messages).toEqual([]);
    expect(result.current.pending).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("sends chat messages and updates state with response", async () => {
    const { result } = renderHook(() => useChatController());

    await waitFor(() => expect(result.current.conversationId).not.toBeNull(), {
      timeout: 5000,
    });

    await act(async () => {
      await result.current.send("Hello from integration test");
    });

    await waitFor(
      () => {
        expect(result.current.messages.length).toBeGreaterThan(0);
      },
      { timeout: 10000 },
    );

    expect(result.current.messages[0].role).toBe("user");
    expect(result.current.messages[0].content).toBe(
      "Hello from integration test",
    );
    expect(result.current.pending).toBe(false);
  });

  it("handles backend errors gracefully", async () => {
    const { result } = renderHook(() => useChatController());

    await waitFor(() => expect(result.current.conversationId).not.toBeNull(), {
      timeout: 5000,
    });

    // Try to send with an invalid conversation ID
    result.current.conversationId = "invalid-id-that-does-not-exist";

    await act(async () => {
      await result.current.send("This should fail");
    });

    // Should either set error or handle gracefully
    expect(result.current.pending).toBe(false);
  });
});
