import { useConversationInitialization } from "@/hooks/useConversationInitialization";
import { useChatStore } from "@/stores/chatStore";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

describe("useConversationInitialization", () => {
  beforeEach(() => {
    useChatStore.getState().reset();
  });

  it("creates a conversation when none exists", async () => {
    const { result } = renderHook(() => useConversationInitialization());

    await waitFor(() => {
      expect(result.current.conversationId).toBe("conv-mock-123");
      expect(result.current.initializing).toBe(false);
    });

    expect(useChatStore.getState().conversationId).toBe("conv-mock-123");
  });
});
