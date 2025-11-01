import { useQuery } from "@tanstack/react-query";
import { API_ENDPOINTS, buildApiUrl } from "../api-config";
import type { Message } from "../hooks/useMessageState";

export interface Conversation {
  id: string;
  title?: string;
  created_at?: string;
  messages?: Message[];
}

export interface ConversationSummary {
  id: string;
  title?: string;
  created_at?: string;
}

/**
 * Query hook for fetching conversation list
 */
export function useConversations() {
  return useQuery<ConversationSummary[]>({
    queryKey: ["conversations"],
    queryFn: async () => {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.CONVERSATIONS));
      if (!response.ok) {
        throw new Error(`Failed to fetch conversations: ${response.status}`);
      }
      const data = await response.json();
      return Array.isArray(data?.data) ? data.data : [];
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Query hook for fetching conversation history
 */
export function useConversationHistoryQuery(
  conversationId: string | undefined,
) {
  return useQuery<Message[]>({
    queryKey: ["conversations", conversationId, "messages"],
    queryFn: async () => {
      if (!conversationId) {
        return [];
      }
      const response = await fetch(
        buildApiUrl(API_ENDPOINTS.CONVERSATION_MESSAGES(conversationId)),
      );
      if (!response.ok) {
        throw new Error(
          `Failed to fetch conversation history: ${response.status}`,
        );
      }
      const data = await response.json();
      return data.messages || [];
    },
    enabled: !!conversationId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Query hook for fetching entity information
 */
export function useEntities() {
  return useQuery<Array<{ id: string; name?: string; type?: string }>>({
    queryKey: ["entities"],
    queryFn: async () => {
      const response = await fetch(buildApiUrl("/v1/entities"));
      if (!response.ok) {
        throw new Error(`Failed to fetch entities: ${response.status}`);
      }
      const data = await response.json();
      return Array.isArray(data?.data) ? data.data : [];
    },
    staleTime: 10 * 60 * 1000, // 10 minutes - entities don't change often
  });
}

/**
 * Query hook for fetching single entity info
 */
export function useEntityInfo(entityId: string | undefined) {
  return useQuery({
    queryKey: ["entities", entityId],
    queryFn: async () => {
      if (!entityId) {
        return null;
      }
      const response = await fetch(
        buildApiUrl(`/v1/entities/${entityId}/info`),
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch entity info: ${response.status}`);
      }
      return response.json();
    },
    enabled: !!entityId,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}
