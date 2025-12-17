/**
 * Chat Store
 *
 * Zustand store for chat state management.
 * Uses SSE (Server-Sent Events) for real-time streaming.
 *
 * Benefits of SSE over WebSocket:
 * - Built-in browser auto-reconnect
 * - Works through all proxies/CDNs
 * - Simpler error handling (standard HTTP errors)
 * - No persistent connection management needed
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { api } from "@/api/client";
import { getSSEClient, resetSSEClient } from "@/api/sse";
import type {
  Message,
  StreamEvent,
  ConversationStep,
  Conversation,
  ReasoningEffort,
} from "@/api/types";

// =============================================================================
// Helpers
// =============================================================================

let stepIdCounter = 0;
let messageIdCounter = 0;

function generateStepId(): string {
  return `step-${Date.now()}-${++stepIdCounter}-${Math.random().toString(36).substring(2, 9)}`;
}

function generateMessageId(): string {
  return `msg-${Date.now()}-${++messageIdCounter}-${Math.random().toString(36).substring(2, 9)}`;
}

function isDuplicateStep(
  existingSteps: ConversationStep[],
  newStep: ConversationStep,
): boolean {
  return existingSteps.some(
    (s) =>
      s.content === newStep.content &&
      s.type === newStep.type &&
      s.kind === newStep.kind &&
      (newStep.kind !== "request" ||
        s.data?.request_id === newStep.data?.request_id),
  );
}

function getWorkflowPhase(event: StreamEvent): string {
  if (event.type === "connected") return "Connected";
  if (event.type === "cancelled") return "Cancelled";
  if (event.type === "workflow.status") {
    if (event.status === "failed") return "Failed";
    if (event.status === "in_progress") return "Starting...";
    return "Processing...";
  }
  if (event.kind === "request") return "Awaiting input...";
  if (event.kind === "routing") return "Routing...";
  if (event.kind === "analysis") return "Analyzing...";
  if (event.kind === "quality") return "Quality check...";
  if (event.kind === "progress") return "Processing...";
  if (event.type === "agent.start")
    return `Starting ${event.author || event.agent_id || "agent"}...`;
  if (event.type === "agent.complete") return "Completing...";
  if (event.type === "agent.message") return "Agent replying...";
  if (event.type === "agent.output") return "Agent outputting...";
  if (event.type === "reasoning.delta") return "Reasoning...";
  return "Processing...";
}

// =============================================================================
// Types
// =============================================================================

interface SendMessageOptions {
  reasoning_effort?: ReasoningEffort;
  enable_checkpointing?: boolean;
}

interface ChatState {
  // Data
  messages: Message[];
  conversations: Conversation[];
  conversationId: string | null;
  activeView: "chat" | "dashboard";

  // Loading states
  isLoading: boolean;
  isInitializing: boolean;
  isConversationsLoading: boolean;

  // Streaming state
  currentReasoning: string;
  isReasoningStreaming: boolean;
  currentWorkflowPhase: string;
  currentAgent: string | null;
  completedPhases: string[];

  // Actions
  loadConversations: () => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  createConversation: (title?: string) => Promise<void>;
  sendMessage: (content: string, options?: SendMessageOptions) => Promise<void>;
  sendWorkflowResponse: (requestId: string, response: unknown) => void;
  cancelStreaming: () => void;
  setMessages: (messages: Message[]) => void;
  setActiveView: (view: "chat" | "dashboard") => void;
  reset: () => void;
}

// =============================================================================
// SSE Client Instance (outside store for serialization)
// =============================================================================

// Message-scoped accumulated content map to prevent race conditions
// Each message ID maps to its accumulated content
const messageContentMap = new Map<string, string>();
let currentStreamingMessageId: string | null = null;

function appendToContent(delta: string): string {
  if (!currentStreamingMessageId) return delta;
  const current = messageContentMap.get(currentStreamingMessageId) || "";
  const updated = current + delta;
  messageContentMap.set(currentStreamingMessageId, updated);
  return updated;
}

function clearMessageContent(messageId: string | undefined): void {
  if (messageId) {
    messageContentMap.delete(messageId);
  }
}

function startNewMessage(messageId: string | undefined): void {
  currentStreamingMessageId = messageId ?? null;
  if (messageId) {
    messageContentMap.set(messageId, "");
  }
}

// =============================================================================
// Store
// =============================================================================

// Store implementation (extracted for conditional devtools wrapping)
// Zustand's set can accept either a partial state or a function returning partial state
type ZustandSet = (
  partial: Partial<ChatState> | ((state: ChatState) => Partial<ChatState>),
) => void;

const storeImpl = (set: ZustandSet, get: () => ChatState): ChatState => ({
  // Initial state
  messages: [],
  conversations: [],
  conversationId: null,
  activeView: "chat",
  isLoading: false,
  isInitializing: true,
  isConversationsLoading: false,
  currentReasoning: "",
  isReasoningStreaming: false,
  currentWorkflowPhase: "",
  currentAgent: null,
  completedPhases: [],

  // =======================
  // Conversation Actions
  // =======================

  loadConversations: async () => {
    set({ isConversationsLoading: true });
    try {
      const convs = await api.listConversations();
      const sorted = convs.sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      );
      set({ conversations: sorted, isInitializing: false });

      // Auto-select first conversation if none selected
      const { conversationId } = get();
      if (!conversationId && sorted.length > 0) {
        await get().selectConversation(sorted[0].id);
      } else if (!conversationId && sorted.length === 0) {
        await get().createConversation();
      }
    } catch (error) {
      console.error("Failed to load conversations:", error);
      set({ isInitializing: false });
    } finally {
      set({ isConversationsLoading: false });
    }
  },

  selectConversation: async (id: string) => {
    try {
      // Stop any active stream before switching conversations.
      get().cancelStreaming();
      const convMessages = await api.loadConversationMessages(id);
      set({
        conversationId: id,
        activeView: "chat",
        messages: convMessages,
        currentReasoning: "",
        isReasoningStreaming: false,
        currentWorkflowPhase: "",
        currentAgent: null,
        completedPhases: [],
        isLoading: false,
      });
    } catch (error) {
      console.error("Failed to load conversation:", error);
    }
  },

  createConversation: async (title = "New Chat") => {
    try {
      // Stop any active stream before starting a new chat.
      get().cancelStreaming();
      const conv = await api.createConversation(title);
      set({
        conversationId: conv.id,
        activeView: "chat",
        messages: [],
        currentReasoning: "",
        isReasoningStreaming: false,
        currentWorkflowPhase: "",
        currentAgent: null,
        completedPhases: [],
        isLoading: false,
      });
      await get().loadConversations();
    } catch (error) {
      console.error("Failed to create conversation:", error);
    }
  },

  // =======================
  // Streaming Actions
  // =======================

  cancelStreaming: () => {
    const sseClient = getSSEClient();
    void sseClient.cancel();
    set({
      isLoading: false,
      isReasoningStreaming: false,
      currentWorkflowPhase: "",
      currentAgent: null,
    });
  },

  sendWorkflowResponse: (requestId: string, response: unknown) => {
    const sseClient = getSSEClient();
    if (!sseClient.isConnected) {
      const errorStep: ConversationStep = {
        id: generateStepId(),
        type: "error",
        content: "Cannot send workflow response: not connected to stream",
        timestamp: new Date().toISOString(),
        data: { request_id: requestId },
      };
      set((state) => {
        const newMessages = [...state.messages];
        const lastIdx = newMessages.length - 1;
        if (newMessages[lastIdx]?.role === "assistant") {
          newMessages[lastIdx] = {
            ...newMessages[lastIdx],
            steps: [...(newMessages[lastIdx].steps || []), errorStep],
          };
        }
        return { messages: newMessages };
      });
      return;
    }

    // Submit response via HTTP POST (SSE is read-only, so we use REST for sends)
    void sseClient.submitResponse(requestId, response).catch((err) => {
      console.error("Failed to submit workflow response:", err);
      const errorStep: ConversationStep = {
        id: generateStepId(),
        type: "error",
        content: `Failed to send response: ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date().toISOString(),
        data: { request_id: requestId },
      };
      set((state) => {
        const newMessages = [...state.messages];
        const lastIdx = newMessages.length - 1;
        if (newMessages[lastIdx]?.role === "assistant") {
          newMessages[lastIdx] = {
            ...newMessages[lastIdx],
            steps: [...(newMessages[lastIdx].steps || []), errorStep],
          };
        }
        return { messages: newMessages };
      });
    });

    const statusStep: ConversationStep = {
      id: generateStepId(),
      type: "status",
      content: "Sent workflow response",
      timestamp: new Date().toISOString(),
      kind: "request",
      data: { request_id: requestId },
    };

    set((state) => {
      const newMessages = [...state.messages];
      const lastIdx = newMessages.length - 1;
      if (newMessages[lastIdx]?.role === "assistant") {
        const steps = newMessages[lastIdx].steps || [];
        if (!isDuplicateStep(steps, statusStep)) {
          newMessages[lastIdx] = {
            ...newMessages[lastIdx],
            steps: [...steps, statusStep],
          };
        }
      }
      return { messages: newMessages };
    });
  },

  setMessages: (messages) => set({ messages }),

  setActiveView: (view) => set({ activeView: view }),

  reset: () => {
    // Disconnect and reset the SSE client singleton
    resetSSEClient();
    // Clear any accumulated message content
    messageContentMap.clear();
    currentStreamingMessageId = null;
    set({
      messages: [],
      conversationId: null,
      activeView: "chat",
      isLoading: false,
      currentReasoning: "",
      isReasoningStreaming: false,
      currentWorkflowPhase: "",
      currentAgent: null,
    });
  },

  // =======================
  // Send Message
  // =======================

  sendMessage: async (content, options) => {
    if (!content.trim()) return;

    const { conversationId } = get();
    let currentConvId = conversationId;

    // Create conversation if needed
    if (!currentConvId) {
      try {
        const conv = await api.createConversation("New Chat");
        currentConvId = conv.id;
        set({ conversationId: conv.id });
        // Ensure sidebar reflects the newly created conversation.
        get()
          .loadConversations()
          .catch((err) => {
            console.error("Failed to refresh conversation list:", err);
            // Optionally show user notification
          });
      } catch (e) {
        console.error("Failed to create conversation:", e);
        return;
      }
    }

    // Create optimistic messages
    const groupId = `group-${Date.now()}`;
    const userMessage: Message = {
      id: generateMessageId(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    const assistantMessage: Message = {
      id: generateMessageId(),
      role: "assistant",
      content: "",
      created_at: new Date().toISOString(),
      steps: [],
      groupId,
      isWorkflowPlaceholder: true,
      workflowPhase: "Starting...",
    };

    // Initialize message-scoped content tracking (fixes race condition)
    startNewMessage(assistantMessage.id);

    set((state) => ({
      messages: [...state.messages, userMessage, assistantMessage],
      isLoading: true,
      currentWorkflowPhase: "Starting...",
      currentAgent: null,
      currentReasoning: "",
      completedPhases: [],
    }));

    // Setup SSE client callbacks
    const sseClient = getSSEClient();
    sseClient.setCallbacks({
      onStatusChange: (status) => {
        if (status === "error") {
          set((state) => {
            const newMessages = [...state.messages];
            const lastIdx = newMessages.length - 1;
            if (newMessages[lastIdx]?.role === "assistant") {
              newMessages[lastIdx] = {
                ...newMessages[lastIdx],
                isWorkflowPlaceholder: false,
                content: "Connection failed. Please try again.",
                workflowPhase: "",
              };
            }
            return { messages: newMessages, isLoading: false };
          });
        }
      },

      onEvent: (event) => {
        handleStreamEvent(event, set, get, assistantMessage.id);
      },

      onComplete: () => {
        // Clean up message content tracking
        clearMessageContent(assistantMessage.id);
        currentStreamingMessageId = null;

        set({
          isLoading: false,
          isReasoningStreaming: false,
          currentReasoning: "",
        });
        // Refresh conversation list (updated_at + previews) after completion.
        void get()
          .loadConversations()
          .catch((err) => {
            console.error("Failed to refresh conversation list:", err);
          });
      },

      onError: (error) => {
        console.error("Stream error:", error);
        const errorStep: ConversationStep = {
          id: generateStepId(),
          type: "error",
          content: error.message || "Unknown error",
          timestamp: new Date().toISOString(),
        };
        set((state) => {
          const newMessages = [...state.messages];
          const lastIdx = newMessages.length - 1;
          if (newMessages[lastIdx]?.role === "assistant") {
            newMessages[lastIdx] = {
              ...newMessages[lastIdx],
              steps: [...(newMessages[lastIdx].steps || []), errorStep],
            };
          }
          return {
            messages: newMessages,
            isLoading: false,
            isReasoningStreaming: false,
          };
        });
      },
    });

    // Connect via SSE (simpler than WebSocket - just GET with query params)
    sseClient.connect(currentConvId!, content, {
      reasoningEffort: options?.reasoning_effort,
      enableCheckpointing: options?.enable_checkpointing,
    });
  },
});

// Conditionally apply devtools middleware only in development
// This prevents exposing sensitive conversation data in production browser devtools
export const useChatStore = create<ChatState>()(
  import.meta.env.DEV ? devtools(storeImpl, { name: "chat-store" }) : storeImpl,
);

// =============================================================================
// Stream Event Handler
// =============================================================================

function handleStreamEvent(
  event: StreamEvent,
  set: ZustandSet,
  _get: () => ChatState,
  _messageId?: string, // Message ID for scoped content tracking
): void {
  // Debug logging for all events (uncomment to troubleshoot)
  console.debug("[chatStore] Event:", event.type, event.kind || "", {
    message: event.message?.substring(0, 100),
    error: event.error,
    status: event.status,
    workflow_id: event.workflow_id,
  });

  const phase = getWorkflowPhase(event);
  set(() => ({ currentWorkflowPhase: phase }));

  if (event.agent_id || event.author) {
    set(() => ({ currentAgent: event.author || event.agent_id || null }));
  }

  // Handle workflow.status events (fallback if mapping doesn't convert)
  if (event.type === "workflow.status") {
    if (event.status === "failed") {
      const errorStep: ConversationStep = {
        id: generateStepId(),
        type: "error",
        content: event.message || event.error || "Workflow failed",
        timestamp: new Date().toISOString(),
        data: event.data,
      };
      set((state) => {
        const newMessages = [...state.messages];
        const lastIdx = newMessages.length - 1;
        if (newMessages[lastIdx]?.role === "assistant") {
          newMessages[lastIdx] = {
            ...newMessages[lastIdx],
            steps: [...(newMessages[lastIdx].steps || []), errorStep],
            isWorkflowPlaceholder: false,
          };
        }
        return {
          messages: newMessages,
          isLoading: false,
          isReasoningStreaming: false,
        };
      });
      return;
    } else if (event.status === "in_progress") {
      const progressStep: ConversationStep = {
        id: generateStepId(),
        type: "progress",
        content: event.message || "Workflow started",
        timestamp: new Date().toISOString(),
        kind: "progress",
        data: event.data,
      };
      set((state) => {
        const newMessages = [...state.messages];
        const lastIdx = newMessages.length - 1;
        if (newMessages[lastIdx]?.role === "assistant") {
          const steps = newMessages[lastIdx].steps || [];
          if (!isDuplicateStep(steps, progressStep)) {
            newMessages[lastIdx] = {
              ...newMessages[lastIdx],
              steps: [...steps, progressStep],
              workflowPhase: phase,
            };
          }
        }
        return { messages: newMessages };
      });
      return;
    }
    // Skip other statuses
    return;
  }

  // Response Delta
  if (event.type === "response.delta" && event.delta) {
    if (event.kind || event.agent_id) {
      // Status/batched update
      const statusStep: ConversationStep = {
        id: generateStepId(),
        type: "status",
        content: `${event.agent_id ? `${event.agent_id}: ` : ""}${event.delta}`,
        timestamp: new Date().toISOString(),
        kind: event.kind,
        data: event.data,
        category: event.category as ConversationStep["category"],
        uiHint: event.ui_hint
          ? {
              component: event.ui_hint.component,
              priority: event.ui_hint.priority,
              collapsible: event.ui_hint.collapsible,
              iconHint: event.ui_hint.icon_hint,
            }
          : undefined,
      };

      set((state) => {
        const newMessages = [...state.messages];
        const lastIdx = newMessages.length - 1;
        if (newMessages[lastIdx]?.role === "assistant") {
          const steps = newMessages[lastIdx].steps || [];
          if (!isDuplicateStep(steps, statusStep)) {
            newMessages[lastIdx] = {
              ...newMessages[lastIdx],
              steps: [...steps, statusStep],
              workflowPhase: phase,
            };
          }
        }
        return { messages: newMessages };
      });
    } else {
      // Direct text delta - use message-scoped tracking to prevent race conditions
      const updatedContent = appendToContent(event.delta);
      set((state) => {
        const newMessages = [...state.messages];
        const lastIdx = newMessages.length - 1;
        if (newMessages[lastIdx]?.role === "assistant") {
          newMessages[lastIdx] = {
            ...newMessages[lastIdx],
            content: updatedContent,
            isWorkflowPlaceholder: false,
          };
        }
        return { messages: newMessages };
      });
    }
  }

  // Orchestrator Messages
  else if (
    event.type === "orchestrator.message" ||
    event.type === "orchestrator.thought"
  ) {
    const newStep: ConversationStep = {
      id: generateStepId(),
      type:
        event.type === "orchestrator.thought"
          ? "thought"
          : event.kind === "request"
            ? "request"
            : "status",
      content: event.message || "",
      timestamp: new Date().toISOString(),
      kind: event.kind,
      data: event.data,
      category: event.category as ConversationStep["category"],
      uiHint: event.ui_hint
        ? {
            component: event.ui_hint.component,
            priority: event.ui_hint.priority,
            collapsible: event.ui_hint.collapsible,
            iconHint: event.ui_hint.icon_hint,
          }
        : undefined,
    };

    // Track phase completion for orchestrator.thought events
    const phaseMap: Record<string, string> = {
      analysis: "Analysis",
      routing: "Routing",
      execution: "Execution",
      progress: "Progress",
      quality: "Quality",
    };

    set((state) => {
      const newMessages = [...state.messages];
      const lastIdx = newMessages.length - 1;

      // Update completed phases if this is a phase completion event
      let newCompletedPhases = state.completedPhases;
      if (
        event.type === "orchestrator.thought" &&
        event.kind &&
        phaseMap[event.kind]
      ) {
        newCompletedPhases = [
          ...new Set([...state.completedPhases, phaseMap[event.kind]]),
        ];
      }

      if (newMessages[lastIdx]?.role === "assistant") {
        const steps = newMessages[lastIdx].steps || [];
        if (!isDuplicateStep(steps, newStep)) {
          newMessages[lastIdx] = {
            ...newMessages[lastIdx],
            steps: [...steps, newStep],
            workflowPhase: phase,
            completedPhases: newCompletedPhases,
          };
        }
      }
      return { messages: newMessages, completedPhases: newCompletedPhases };
    });
  }

  // Agent Events
  else if (
    event.type === "agent.start" ||
    event.type === "agent.complete" ||
    event.type === "agent.output" ||
    event.type === "agent.thought" ||
    event.type === "agent.message"
  ) {
    const agentLabel = event.author || event.agent_id || "agent";
    const mappedType: ConversationStep["type"] =
      event.type === "agent.start"
        ? "agent_start"
        : event.type === "agent.complete"
          ? "agent_complete"
          : event.type === "agent.output"
            ? "agent_output"
            : event.type === "agent.message"
              ? "agent_output"
              : "agent_thought";

    const stepContent =
      event.type === "agent.thought"
        ? `${agentLabel}: ${event.message || event.content || "Thinking..."}`
        : event.type === "agent.output" || event.type === "agent.message"
          ? `${agentLabel}: Produced output`
          : `${agentLabel}: ${event.message || event.content || (event.type === "agent.start" ? "Starting..." : "Completed")}`;

    const newStep: ConversationStep = {
      id: generateStepId(),
      type: mappedType,
      content: stepContent,
      timestamp: new Date().toISOString(),
      kind: event.kind,
      data: {
        ...event.data,
        agent_id: event.agent_id,
        author: event.author,
        output:
          event.type === "agent.output" || event.type === "agent.message"
            ? event.message || event.content
            : undefined,
      },
      category: event.category as ConversationStep["category"],
    };

    set((state) => {
      const newMessages = [...state.messages];
      const lastIdx = newMessages.length - 1;
      if (newMessages[lastIdx]?.role === "assistant") {
        const steps = newMessages[lastIdx].steps || [];
        if (!isDuplicateStep(steps, newStep)) {
          const updatedMsg = {
            ...newMessages[lastIdx],
            steps: [...steps, newStep],
            workflowPhase: phase,
          };
          newMessages[lastIdx] = updatedMsg;
        }
      }
      return { messages: newMessages };
    });
  }

  // Response Completed
  else if (event.type === "response.completed") {
    const finalContent = event.message || "";
    set((state) => {
      const newMessages = [...state.messages];
      const lastIdx = newMessages.length - 1;
      if (newMessages[lastIdx]?.role === "assistant") {
        newMessages[lastIdx] = {
          ...newMessages[lastIdx],
          content: finalContent || newMessages[lastIdx].content,
          author: finalContent ? "Final Answer" : newMessages[lastIdx].author,
          isWorkflowPlaceholder: false,
          workflowPhase: "",
          qualityFlag: event.quality_flag,
          qualityScore: event.quality_score,
          completedPhases: state.completedPhases,
        };
      }
      return {
        messages: newMessages,
        currentWorkflowPhase: "",
        currentAgent: null,
      };
    });
  }

  // Reasoning
  else if (event.type === "reasoning.delta" && event.reasoning) {
    const reasoningDelta = event.reasoning;

    set((state) => {
      const newContent = state.currentReasoning + reasoningDelta;
      const newMessages = [...state.messages];
      const lastIdx = newMessages.length - 1;
      if (newMessages[lastIdx]?.role === "assistant") {
        // Update existing reasoning step or create one
        const steps = newMessages[lastIdx].steps || [];
        const existingReasoningIdx = steps.findIndex(
          (s) => s.type === "reasoning",
        );
        let newSteps: ConversationStep[];
        if (existingReasoningIdx >= 0) {
          newSteps = [...steps];
          newSteps[existingReasoningIdx] = {
            ...newSteps[existingReasoningIdx],
            content: newContent,
          };
        } else {
          newSteps = [
            ...steps,
            {
              id: generateStepId(),
              type: "reasoning",
              content: newContent,
              timestamp: new Date().toISOString(),
              data: { agent_id: event.agent_id },
            },
          ];
        }
        newMessages[lastIdx] = {
          ...newMessages[lastIdx],
          steps: newSteps,
          workflowPhase: "Reasoning...",
        };
      }
      return {
        currentReasoning: newContent,
        isReasoningStreaming: true,
        messages: newMessages,
      };
    });
  }

  // Reasoning Completed
  else if (event.type === "reasoning.completed") {
    set(() => ({ isReasoningStreaming: false }));
  }

  // Error
  else if (event.type === "error") {
    console.error("Stream error:", event.error);
    const errorStep: ConversationStep = {
      id: generateStepId(),
      type: "error",
      content: event.error || "Unknown error",
      timestamp: new Date().toISOString(),
    };
    set((state) => {
      const newMessages = [...state.messages];
      const lastIdx = newMessages.length - 1;
      if (newMessages[lastIdx]?.role === "assistant") {
        newMessages[lastIdx] = {
          ...newMessages[lastIdx],
          steps: [...(newMessages[lastIdx].steps || []), errorStep],
        };
      }
      return {
        messages: newMessages,
        isLoading: false,
        isReasoningStreaming: false,
      };
    });
  }
}
