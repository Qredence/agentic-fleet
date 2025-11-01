/**
 * useConversationHistory Hook
 *
 * Manages loading and parsing conversation history
 */

import { useCallback } from "react";
import { API_ENDPOINTS, buildApiUrl } from "../lib/api-config";
import type { Message } from "./useMessageState";

export interface UseConversationHistoryReturn {
  loadHistory: (conversationId: string) => Promise<Message[]>;
}

export function useConversationHistory(): UseConversationHistoryReturn {
  const loadHistory = useCallback(
    async (conversationId: string): Promise<Message[]> => {
      try {
        const response = await fetch(
          buildApiUrl(API_ENDPOINTS.CONVERSATION_MESSAGES(conversationId)),
        );

        if (!response.ok) {
          throw new Error(
            `Failed to load conversation history: ${response.status}`,
          );
        }

        const data = (await response.json()) as {
          messages: Array<{
            id: string;
            role: "user" | "assistant" | "system";
            content: string;
            actor?: string;
          }>;
        };

        return data.messages || [];
      } catch (error) {
        console.error("Error loading conversation history:", error);
        return [];
      }
    },
    [],
  );

  return {
    loadHistory,
  };
}
