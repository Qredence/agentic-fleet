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

const UI_PREFERENCE_KEYS = {
  showTrace: "agenticfleet:ui:showTrace",
  showRawReasoning: "agenticfleet:ui:showRawReasoning",
  executionMode: "agenticfleet:ui:executionMode",
  enableGepa: "agenticfleet:ui:enableGepa",
} as const;

function getStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function readBoolPreference(key: string, fallback: boolean): boolean {
  const storage = getStorage();
  if (!storage) return fallback;
  const raw = storage.getItem(key);
  if (raw === null) return fallback;
  if (raw === "1" || raw === "true") return true;
  if (raw === "0" || raw === "false") return false;
  return fallback;
}

function writeBoolPreference(key: string, value: boolean): void {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.setItem(key, value ? "1" : "0");
  } catch {
    // Ignore quota / privacy mode errors
  }
}

function readStringPreference(key: string, fallback: string): string {
  const storage = getStorage();
  if (!storage) return fallback;
  const raw = storage.getItem(key);
  return raw ?? fallback;
}

function writeStringPreference(key: string, value: string): void {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.setItem(key, value);
  } catch {
    // Ignore quota / privacy mode errors
  }
}

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

  // UI preferences
  showTrace: boolean;
  showRawReasoning: boolean;
  executionMode: "auto" | "fast" | "standard";
  enableGepa: boolean;

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
  setShowTrace: (show: boolean) => void;
  setShowRawReasoning: (show: boolean) => void;
  setExecutionMode: (mode: "auto" | "fast" | "standard") => void;
  setEnableGepa: (enable: boolean) => void;
  reset: () => void;
}

// =============================================================================
// SSE Client Instance (outside store for serialization)
// =============================================================================

// Message-scoped accumulated content map to prevent race conditions.
// Keyed by assistant message ID so the store stays correct even if multiple streams overlap.
const messageContentMap = new Map<string, string>();

function appendToContent(messageId: string, delta: string): string {
  const current = messageContentMap.get(messageId) || "";
  const updated = current + delta;
  messageContentMap.set(messageId, updated);
  return updated;
}

function clearMessageContent(messageId: string | undefined): void {
  if (messageId) messageContentMap.delete(messageId);
}

function startNewMessage(messageId: string | undefined): void {
  if (messageId) messageContentMap.set(messageId, "");
}

// =============================================================================
// Message Update Helpers (reduce duplication)
// =============================================================================

/**
 * Helper to update the last assistant message with a transformation function.
 * Reduces ~150 lines of duplicated message update logic throughout the store.
 */
function updateLastAssistantMessage(
  state: ChatState,
  updater: (msg: Message) => Partial<Message>,
): Partial<ChatState> {
  const newMessages = [...state.messages];
  const lastIdx = newMessages.length - 1;
  if (lastIdx >= 0 && newMessages[lastIdx]?.role === "assistant") {
    newMessages[lastIdx] = {
      ...newMessages[lastIdx],
      ...updater(newMessages[lastIdx]),
    };
  }
  return { messages: newMessages };
}

/**
 * Helper to add a step to the last assistant message.
 */
function addStepToLastMessage(
  state: ChatState,
  step: ConversationStep,
  checkDuplicate = true,
): Partial<ChatState> {
  const newMessages = [...state.messages];
  const lastIdx = newMessages.length - 1;
  if (lastIdx >= 0 && newMessages[lastIdx]?.role === "assistant") {
    const steps = newMessages[lastIdx].steps || [];
    if (!checkDuplicate || !isDuplicateStep(steps, step)) {
      newMessages[lastIdx] = {
        ...newMessages[lastIdx],
        steps: [...steps, step],
      };
    }
  }
  return { messages: newMessages };
}

/**
 * Factory function to create error steps with consistent structure.
 */
function createErrorStep(
  content: string,
  data?: Record<string, unknown>,
): ConversationStep {
  return {
    id: generateStepId(),
    type: "error",
    content,
    timestamp: new Date().toISOString(),
    data,
  };
}

/**
 * Factory function to create status steps with consistent structure.
 */
function createStatusStep(
  content: string,
  kind?: string,
  data?: Record<string, unknown>,
  options?: {
    category?: ConversationStep["category"];
    uiHint?: ConversationStep["uiHint"];
  },
): ConversationStep {
  return {
    id: generateStepId(),
    type: "status",
    content,
    timestamp: new Date().toISOString(),
    kind,
    data,
    category: options?.category,
    uiHint: options?.uiHint,
  };
}

/**
 * Factory function to create progress steps with consistent structure.
 */
function createProgressStep(
  content: string,
  kind: string,
  data?: Record<string, unknown>,
): ConversationStep {
  return {
    id: generateStepId(),
    type: "progress",
    content,
    timestamp: new Date().toISOString(),
    kind,
    data,
  };
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
  showTrace: readBoolPreference(UI_PREFERENCE_KEYS.showTrace, true),
  showRawReasoning: readBoolPreference(
    UI_PREFERENCE_KEYS.showRawReasoning,
    false,
  ),
  executionMode: readStringPreference(
    UI_PREFERENCE_KEYS.executionMode,
    "auto",
  ) as "auto" | "fast" | "standard",
  enableGepa: readBoolPreference(UI_PREFERENCE_KEYS.enableGepa, false),
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

    // Clear any accumulated content for the currently streaming assistant message.
    const lastAssistantId = (() => {
      const msgs = get().messages;
      for (let i = msgs.length - 1; i >= 0; i -= 1) {
        if (msgs[i]?.role === "assistant" && msgs[i].id) return msgs[i].id;
      }
      return undefined;
    })();
    clearMessageContent(lastAssistantId);

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
      const errorStep = createErrorStep(
        "Cannot send workflow response: not connected to stream",
        { request_id: requestId },
      );
      set((state) => addStepToLastMessage(state, errorStep, false));
      return;
    }

    // Submit response via HTTP POST (SSE is read-only, so we use REST for sends)
    void sseClient.submitResponse(requestId, response).catch((err) => {
      console.error("Failed to submit workflow response:", err);
      const errorStep = createErrorStep(
        `Failed to send response: ${err instanceof Error ? err.message : "Unknown error"}`,
        { request_id: requestId },
      );
      set((state) => addStepToLastMessage(state, errorStep, false));
    });

    const statusStep = createStatusStep("Sent workflow response", "request", {
      request_id: requestId,
    });

    set((state) => addStepToLastMessage(state, statusStep));
  },

  setMessages: (messages) => set({ messages }),

  setActiveView: (view) => set({ activeView: view }),

  setShowTrace: (show) => {
    writeBoolPreference(UI_PREFERENCE_KEYS.showTrace, show);
    set({ showTrace: show });
  },

  setShowRawReasoning: (show) => {
    writeBoolPreference(UI_PREFERENCE_KEYS.showRawReasoning, show);
    set({ showRawReasoning: show });
  },

  setExecutionMode: (mode) => {
    writeStringPreference(UI_PREFERENCE_KEYS.executionMode, mode);
    set({ executionMode: mode });
  },

  setEnableGepa: (enable) => {
    writeBoolPreference(UI_PREFERENCE_KEYS.enableGepa, enable);
    set({ enableGepa: enable });
  },

  reset: () => {
    // Disconnect and reset the SSE client singleton
    resetSSEClient();
    // Clear any accumulated message content
    messageContentMap.clear();
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
          set((state) => ({
            ...updateLastAssistantMessage(state, () => ({
              isWorkflowPlaceholder: false,
              content: "Connection failed. Please try again.",
              workflowPhase: "",
            })),
            isLoading: false,
          }));
        }
      },

      onEvent: (event) => {
        handleStreamEvent(event, set, get, assistantMessage.id);
      },

      onComplete: () => {
        // Clean up message content tracking
        clearMessageContent(assistantMessage.id);

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
        const errorStep = createErrorStep(error.message || "Unknown error");
        set((state) => ({
          ...addStepToLastMessage(state, errorStep, false),
          isLoading: false,
          isReasoningStreaming: false,
        }));
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
  messageId?: string, // Message ID for scoped content tracking
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
      const errorStep = createErrorStep(
        event.message || event.error || "Workflow failed",
        event.data,
      );
      set((state) => {
        const withStep = addStepToLastMessage(state, errorStep, false);
        const withUpdate = updateLastAssistantMessage(
          { ...state, ...withStep },
          () => ({ isWorkflowPlaceholder: false }),
        );
        return {
          ...withUpdate,
          isLoading: false,
          isReasoningStreaming: false,
        };
      });
      return;
    } else if (event.status === "in_progress") {
      const progressStep = createProgressStep(
        event.message || "Workflow started",
        "progress",
        event.data,
      );
      set((state) => ({
        ...addStepToLastMessage(state, progressStep),
        ...updateLastAssistantMessage(state, () => ({
          workflowPhase: phase,
        })),
      }));
      return;
    }
    // Skip other statuses
    return;
  }

  // Response Delta
  if (event.type === "response.delta" && event.delta) {
    if (event.kind || event.agent_id) {
      // Status/batched update
      const statusStep = createStatusStep(
        `${event.agent_id ? `${event.agent_id}: ` : ""}${event.delta}`,
        event.kind,
        event.data,
        {
          category: event.category as ConversationStep["category"],
          uiHint: event.ui_hint
            ? {
                component: event.ui_hint.component,
                priority: event.ui_hint.priority,
                collapsible: event.ui_hint.collapsible,
                iconHint: event.ui_hint.icon_hint,
              }
            : undefined,
        },
      );

      set((state) => ({
        ...addStepToLastMessage(state, statusStep),
        ...updateLastAssistantMessage(state, () => ({
          workflowPhase: phase,
        })),
      }));
    } else {
      // Direct text delta - use message-scoped tracking to prevent race conditions
      const updatedContent = messageId
        ? appendToContent(messageId, event.delta)
        : event.delta;
      set((state) =>
        updateLastAssistantMessage(state, () => ({
          content: updatedContent,
          isWorkflowPlaceholder: false,
        })),
      );
    }
  }

  // Orchestrator Messages
  else if (
    event.type === "orchestrator.message" ||
    event.type === "orchestrator.thought"
  ) {
    const stepType: ConversationStep["type"] =
      event.type === "orchestrator.thought"
        ? "thought"
        : event.kind === "request"
          ? "request"
          : "status";

    const newStep: ConversationStep = {
      id: generateStepId(),
      type: stepType,
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

    const newCompletedPhases =
      event.type === "orchestrator.thought" &&
      event.kind &&
      phaseMap[event.kind]
        ? [...new Set([..._get().completedPhases, phaseMap[event.kind]])]
        : _get().completedPhases;

    set((state) => ({
      ...addStepToLastMessage(state, newStep),
      ...updateLastAssistantMessage(state, () => ({
        workflowPhase: phase,
        completedPhases: newCompletedPhases,
      })),
      completedPhases: newCompletedPhases,
    }));
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

    set((state) => ({
      ...addStepToLastMessage(state, newStep),
      ...updateLastAssistantMessage(state, () => ({
        workflowPhase: phase,
      })),
    }));
  }

  // Response Completed
  else if (event.type === "response.completed") {
    const finalContent = event.message || "";
    set((state) => ({
      ...updateLastAssistantMessage(state, (msg) => ({
        content: finalContent || msg.content,
        author: finalContent ? "Final Answer" : msg.author,
        isWorkflowPlaceholder: false,
        workflowPhase: "",
        qualityFlag: event.quality_flag,
        qualityScore: event.quality_score,
        completedPhases: state.completedPhases,
      })),
      currentWorkflowPhase: "",
      currentAgent: null,
    }));
  }

  // Reasoning
  else if (event.type === "reasoning.delta" && event.reasoning) {
    const reasoningDelta = event.reasoning;

    set((state) => {
      const newContent = state.currentReasoning + reasoningDelta;
      const newMessages = [...state.messages];
      const lastIdx = newMessages.length - 1;
      if (lastIdx >= 0 && newMessages[lastIdx]?.role === "assistant") {
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
    const errorStep = createErrorStep(event.error || "Unknown error");
    set((state) => ({
      ...addStepToLastMessage(state, errorStep, false),
      isLoading: false,
      isReasoningStreaming: false,
    }));
  }
}
