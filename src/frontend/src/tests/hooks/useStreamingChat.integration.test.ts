import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, beforeAll, beforeEach } from "vitest";
import { useStreamingChat } from "@/hooks/useStreamingChat";
import { createConversation } from "@/lib/api/chatApi";

// Integration tests - no mocks, real backend required
const RUN_INTEGRATION = process.env.RUN_LIVE_CHAT === "1";

describe.skipIf(!RUN_INTEGRATION)(
  "useStreamingChat - Integration Tests",
  () => {
    let realFetch: typeof globalThis.fetch | undefined;

    beforeAll(() => {
      // Capture the real fetch implementation before mocks run.
      realFetch = globalThis.fetch;
    });

    beforeEach(() => {
      // Restore real fetch for integration tests
      if (realFetch) {
        globalThis.fetch = realFetch;
      }
    });

    it("sends chat message and receives streaming response", async () => {
      // 1. Create a conversation first
      const conversation = await createConversation({
        title: "Integration Test Chat",
      });
      expect(conversation.id).toBeDefined();

      // 2. Setup the hook with completion tracking
      let completedContent = "";
      let messageCompleted = false;
      const onMessageComplete = (content: string) => {
        completedContent = content;
        messageCompleted = true;
      };

      const { result } = renderHook(() =>
        useStreamingChat({
          onMessageComplete,
          onError: (error: unknown) => console.error("Stream error:", error),
        }),
      );

      // 3. Send a message (don't wait for it to complete)
      act(() => {
        result.current.sendMessage(conversation.id, "Hello, are you there?");
      });

      // 4. Wait for the message to complete
      await waitFor(
        () => {
          expect(messageCompleted).toBe(true);
        },
        { timeout: 15000 },
      );

      // 5. Verify content was received
      expect(completedContent).toBeTruthy();
      expect(completedContent.length).toBeGreaterThan(0);
      expect(result.current.streamingContent).toBe(completedContent);
      expect(result.current.isStreaming).toBe(false);
    });
  },
);
