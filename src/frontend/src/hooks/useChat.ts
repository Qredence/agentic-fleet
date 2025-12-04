import { useState, useRef, useCallback, useEffect } from "react";
import ReconnectingWebSocket from "reconnecting-websocket";
import { api } from "../api/client";
import type {
  Message,
  StreamEvent,
  ConversationStep,
  Conversation,
  ChatRequest,
} from "../api/types";

// Generate unique IDs for steps and messages to avoid React key collisions
let stepIdCounter = 0;
let messageIdCounter = 0;
function generateStepId(): string {
  return `step-${Date.now()}-${++stepIdCounter}-${Math.random().toString(36).substring(2, 9)}`;
}
function generateMessageId(): string {
  return `msg-${Date.now()}-${++messageIdCounter}-${Math.random().toString(36).substring(2, 9)}`;
}

interface SendMessageOptions {
  reasoning_effort?: "minimal" | "medium" | "maximal";
}

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  isInitializing: boolean;
  currentReasoning: string;
  isReasoningStreaming: boolean;
  currentWorkflowPhase: string;
  currentAgent: string | null;
  sendMessage: (content: string, options?: SendMessageOptions) => Promise<void>;
  cancelStreaming: () => void;
  conversationId: string | null;
  createConversation: () => Promise<void>;
  conversations: Conversation[];
  loadConversations: () => Promise<Conversation[]>;
  selectConversation: (id: string) => Promise<void>;
  isConversationsLoading: boolean;
}

// Workflow phase mapping based on event types and kinds
function getWorkflowPhase(event: StreamEvent): string {
  if (event.type === "connected") return "Connected";
  if (event.type === "cancelled") return "Cancelled";
  if (event.kind === "routing") return "Routing...";
  if (event.kind === "analysis") return "Analyzing...";
  if (event.kind === "quality") return "Quality check...";
  if (event.kind === "progress") return "Processing...";
  if (event.type === "agent.start")
    return `Starting ${event.author || event.agent_id || "agent"}...`;
  if (event.type === "agent.complete") return "Completing...";
  if (event.type === "reasoning.delta") return "Reasoning...";
  return "Processing...";
}

export const useChat = (): UseChatReturn => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isConversationsLoading, setIsConversationsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentReasoning, setCurrentReasoning] = useState<string>("");
  const [isReasoningStreaming, setIsReasoningStreaming] = useState(false);
  const [currentWorkflowPhase, setCurrentWorkflowPhase] = useState<string>("");
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const wsRef = useRef<ReconnectingWebSocket | null>(null);
  const currentGroupIdRef = useRef<string>("");
  const accumulatedContentRef = useRef<string>("");
  const isInitializedRef = useRef(false);

  const cancelStreaming = useCallback(() => {
    if (wsRef.current) {
      // Send cancel message before closing
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "cancel" }));
      }
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsLoading(false);
    setIsReasoningStreaming(false);
    setCurrentWorkflowPhase("");
    setCurrentAgent(null);
  }, []);

  const loadConversations = useCallback(async () => {
    setIsConversationsLoading(true);
    try {
      const convs = await api.listConversations();
      // Sort by updated_at descending (most recent first)
      const sorted = convs.sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      );
      setConversations(sorted);
      return sorted;
    } catch (error) {
      console.error("Failed to load conversations:", error);
      return [];
    } finally {
      setIsConversationsLoading(false);
      setIsInitializing(false);
    }
  }, []);

  const selectConversation = useCallback(async (id: string) => {
    try {
      const convMessages = await api.loadConversationMessages(id);
      setConversationId(id);
      setMessages(convMessages);
      setCurrentReasoning("");
      setIsReasoningStreaming(false);
      setCurrentWorkflowPhase("");
      setCurrentAgent(null);
    } catch (error) {
      console.error("Failed to load conversation:", error);
    }
  }, []);

  const createConversation = useCallback(async () => {
    try {
      const conv = await api.createConversation("New Chat");
      setConversationId(conv.id);
      setMessages([]);
      // Refresh conversation list
      await loadConversations();
    } catch (error) {
      console.error("Failed to create conversation:", error);
    }
  }, [loadConversations]);

  useEffect(() => {
    // Prevent double initialization in React StrictMode or HMR
    if (isInitializedRef.current) return;
    isInitializedRef.current = true;

    let cancelled = false;

    (async () => {
      const convs = await loadConversations();
      if (cancelled) return;

      if (convs.length > 0) {
        await selectConversation(convs[0].id);
      } else {
        await createConversation();
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleStreamEvent = useCallback(
    (data: StreamEvent, groupId: string) => {
      if (data.type === "heartbeat") {
        return;
      }
      // Update workflow phase for shimmer display
      const phase = getWorkflowPhase(data);
      setCurrentWorkflowPhase(phase);

      // Track current agent for typing indicator
      if (data.agent_id || data.author) {
        setCurrentAgent(data.author || data.agent_id || null);
      }

      if (data.type === "response.delta" && data.delta) {
        if (data.kind || data.agent_id) {
          const statusStep: ConversationStep = {
            id: generateStepId(),
            type: "status",
            content: `${data.agent_id ? `${data.agent_id}: ` : ""}${data.delta}`,
            timestamp: new Date().toISOString(),
            kind: data.kind,
            data: data.data,
            category: data.category as ConversationStep["category"],
            uiHint: data.ui_hint
              ? {
                  component: data.ui_hint.component,
                  priority: data.ui_hint.priority,
                  collapsible: data.ui_hint.collapsible,
                  iconHint: data.ui_hint.icon_hint,
                }
              : undefined,
          };

          setMessages((prev) => {
            const newMessages = [...prev];
            let placeholderIdx = -1;
            for (let i = newMessages.length - 1; i >= 0; i--) {
              if (newMessages[i].role === "assistant") {
                placeholderIdx = i;
                break;
              }
            }
            if (placeholderIdx >= 0) {
              const currentSteps = newMessages[placeholderIdx].steps || [];
              newMessages[placeholderIdx] = {
                ...newMessages[placeholderIdx],
                steps: [...currentSteps, statusStep],
                workflowPhase: phase,
              };
            }
            return newMessages;
          });
        } else {
          // Direct, unbatched text update for minimal latency
          const delta = data.delta;
          accumulatedContentRef.current += delta;
          const contentSnapshot = accumulatedContentRef.current;
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastMsgIndex = newMessages.length - 1;
            if (newMessages[lastMsgIndex]?.role === "assistant") {
              newMessages[lastMsgIndex] = {
                ...newMessages[lastMsgIndex],
                content: contentSnapshot,
                isWorkflowPlaceholder: false,
              };
            }
            return newMessages;
          });
        }
      } else if (data.type === "connected") {
        const connectStep: ConversationStep = {
          id: generateStepId(),
          type: "status",
          content: "Connected",
          timestamp: new Date().toISOString(),
          kind: "status",
          category: data.category as ConversationStep["category"],
        };

        setMessages((prev) => {
          const newMessages = [...prev];
          let placeholderIdx = -1;
          for (let i = newMessages.length - 1; i >= 0; i--) {
            if (newMessages[i].role === "assistant") {
              placeholderIdx = i;
              break;
            }
          }
          if (placeholderIdx >= 0) {
            const currentSteps = newMessages[placeholderIdx].steps || [];
            newMessages[placeholderIdx] = {
              ...newMessages[placeholderIdx],
              steps: [...currentSteps, connectStep],
              workflowPhase: "Connected",
            };
          }
          return newMessages;
        });
      } else if (
        data.type === "orchestrator.message" ||
        data.type === "orchestrator.thought"
      ) {
        const newStep: ConversationStep = {
          id: generateStepId(),
          type: data.type === "orchestrator.thought" ? "thought" : "status",
          content: data.message || "",
          timestamp: new Date().toISOString(),
          kind: data.kind,
          data: data.data,
          category: data.category as ConversationStep["category"],
          uiHint: data.ui_hint
            ? {
                component: data.ui_hint.component,
                priority: data.ui_hint.priority,
                collapsible: data.ui_hint.collapsible,
                iconHint: data.ui_hint.icon_hint,
              }
            : undefined,
        };

        setMessages((prev) => {
          const newMessages = [...prev];
          let placeholderIdx = -1;
          for (let i = newMessages.length - 1; i >= 0; i--) {
            if (newMessages[i].role === "assistant") {
              placeholderIdx = i;
              break;
            }
          }
          if (placeholderIdx >= 0) {
            const currentSteps = newMessages[placeholderIdx].steps || [];
            newMessages[placeholderIdx] = {
              ...newMessages[placeholderIdx],
              steps: [...currentSteps, newStep],
              workflowPhase: phase,
            };
          }
          return newMessages;
        });
      } else if (
        data.type === "agent.start" ||
        data.type === "agent.complete" ||
        data.type === "agent.output" ||
        data.type === "agent.thought" ||
        data.type === "agent.message"
      ) {
        const agentLabel = data.author || data.agent_id || "agent";
        const mappedAgentType: ConversationStep["type"] =
          data.type === "agent.start"
            ? "agent_start"
            : data.type === "agent.complete"
              ? "agent_complete"
              : data.type === "agent.output"
                ? "agent_output"
                : data.type === "agent.message"
                  ? "agent_output"
                  : "agent_thought";

        if (
          data.type === "agent.start" ||
          data.type === "agent.complete" ||
          data.type === "agent.thought"
        ) {
          const stepContent =
            data.type === "agent.thought"
              ? `${agentLabel}: ${data.message || data.content || "Thinking..."}`
              : `${agentLabel}: ${data.message || data.content || (data.type === "agent.start" ? "Starting..." : "Completed")}`;

          const newStep: ConversationStep = {
            id: generateStepId(),
            type: mappedAgentType,
            content: stepContent,
            timestamp: new Date().toISOString(),
            kind: data.kind,
            data: {
              ...data.data,
              agent_id: data.agent_id,
              author: data.author,
            },
            category: data.category as ConversationStep["category"],
            uiHint: data.ui_hint
              ? {
                  component: data.ui_hint.component,
                  priority: data.ui_hint.priority,
                  collapsible: data.ui_hint.collapsible,
                  iconHint: data.ui_hint.icon_hint,
                }
              : undefined,
          };

          setMessages((prev) => {
            const newMessages = [...prev];
            for (let i = newMessages.length - 1; i >= 0; i--) {
              if (newMessages[i].role === "assistant") {
                const currentSteps = newMessages[i].steps || [];
                newMessages[i] = {
                  ...newMessages[i],
                  steps: [...currentSteps, newStep],
                  workflowPhase: phase,
                };
                break;
              }
            }
            return newMessages;
          });
        }

        if (
          (data.type === "agent.message" || data.type === "agent.output") &&
          (data.message || data.content)
        ) {
          const agentContent = data.message || data.content || "";
          const isCompleteOutput = data.type === "agent.output";
          const reasoningStep: ConversationStep = {
            id: generateStepId(),
            type: "reasoning",
            content: agentContent,
            timestamp: new Date().toISOString(),
            data: { agent_id: data.agent_id, author: data.author },
            category: data.category as ConversationStep["category"],
            uiHint: data.ui_hint
              ? {
                  component: data.ui_hint.component,
                  priority: data.ui_hint.priority,
                  collapsible: data.ui_hint.collapsible,
                  iconHint: data.ui_hint.icon_hint,
                }
              : undefined,
          };

          setMessages((prev) => {
            const newMessages = [...prev];
            const lastMsgIndex = newMessages.length - 1;
            const lastMsg = newMessages[lastMsgIndex];

            if (!lastMsg) {
              const newAgentMessage: Message = {
                id: generateMessageId(),
                role: "assistant",
                content: agentContent,
                created_at: new Date().toISOString(),
                author: agentLabel,
                agent_id: data.agent_id,
                groupId,
                isWorkflowPlaceholder: false,
              };
              newMessages.push(newAgentMessage);
              // Attach reasoning step to the same assistant entry we just added
              newMessages[newMessages.length - 1].steps = [reasoningStep];
              return newMessages;
            }

            if (
              lastMsg.role === "assistant" &&
              lastMsg.isWorkflowPlaceholder &&
              !lastMsg.content
            ) {
              newMessages[lastMsgIndex] = {
                ...lastMsg,
                content: agentContent,
                author: agentLabel,
                agent_id: data.agent_id ?? lastMsg.agent_id,
                isWorkflowPlaceholder: false,
                workflowPhase: undefined,
              };
            } else if (
              lastMsg.role === "assistant" &&
              lastMsg.author !== agentLabel
            ) {
              const newAgentMessage: Message = {
                id: generateMessageId(),
                role: "assistant",
                content: agentContent,
                created_at: new Date().toISOString(),
                author: agentLabel,
                agent_id: data.agent_id,
                groupId,
                isWorkflowPlaceholder: false,
              };
              newMessages.push(newAgentMessage);
            } else {
              for (let i = newMessages.length - 1; i >= 0; i--) {
                if (newMessages[i].role === "assistant") {
                  const existingContent = newMessages[i].content || "";
                  const newContent = isCompleteOutput
                    ? agentContent
                    : existingContent
                      ? `${existingContent}\n\n${agentContent}`
                      : agentContent;
                  newMessages[i] = {
                    ...newMessages[i],
                    content: newContent,
                    author: agentLabel,
                    agent_id: data.agent_id ?? newMessages[i].agent_id,
                    isWorkflowPlaceholder: false,
                  };
                  break;
                }
              }
            }
            // Append reasoning step to the assistant message we updated/created
            for (let i = newMessages.length - 1; i >= 0; i--) {
              if (newMessages[i].role === "assistant") {
                const currentSteps = newMessages[i].steps || [];
                newMessages[i] = {
                  ...newMessages[i],
                  steps: [...currentSteps, reasoningStep],
                };
                break;
              }
            }
            return newMessages;
          });
        }
      } else if (data.type === "response.completed") {
        if (data.message && data.message.trim().length > 0) {
          const finalContent = data.message;
          const finalTrim = finalContent.trim();

          setMessages((prev) => {
            const newMessages = [...prev];
            let lastAssistantIdx = -1;
            for (let i = newMessages.length - 1; i >= 0; i--) {
              if (newMessages[i].role === "assistant") {
                lastAssistantIdx = i;
                break;
              }
            }

            if (lastAssistantIdx >= 0) {
              const lastMsg = newMessages[lastAssistantIdx];
              const lastTrim = (lastMsg.content || "").trim();

              if (
                !lastMsg.content ||
                lastTrim.length === 0 ||
                lastMsg.isWorkflowPlaceholder
              ) {
                newMessages[lastAssistantIdx] = {
                  ...lastMsg,
                  content: finalContent,
                  author: "Final Answer",
                  isWorkflowPlaceholder: false,
                  workflowPhase: undefined,
                  qualityFlag: data.quality_flag,
                  qualityScore: data.quality_score,
                };
              } else if (lastTrim !== finalTrim) {
                const finalAnswerMessage: Message = {
                  id: generateMessageId(),
                  role: "assistant",
                  content: finalContent,
                  created_at: new Date().toISOString(),
                  author: "Final Answer",
                  groupId,
                  isWorkflowPlaceholder: false,
                  qualityFlag: data.quality_flag,
                  qualityScore: data.quality_score,
                };
                newMessages.push(finalAnswerMessage);
              }
            }
            return newMessages;
          });
        }
        setCurrentWorkflowPhase("");
        setCurrentAgent(null);
      } else if (data.type === "error") {
        console.error("Stream error event:", data.error);
        const errorStep: ConversationStep = {
          id: generateStepId(),
          type: "error",
          content: data.error || "Unknown error",
          timestamp: new Date().toISOString(),
          data: data.reasoning_partial
            ? { reasoning_partial: true }
            : undefined,
          category: data.category as ConversationStep["category"],
          uiHint: data.ui_hint
            ? {
                component: data.ui_hint.component,
                priority: data.ui_hint.priority,
                collapsible: data.ui_hint.collapsible,
                iconHint: data.ui_hint.icon_hint,
              }
            : undefined,
        };
        setMessages((prev) => {
          const newMessages = [...prev];
          let placeholderIdx = -1;
          for (let i = newMessages.length - 1; i >= 0; i--) {
            if (newMessages[i].role === "assistant") {
              placeholderIdx = i;
              break;
            }
          }
          if (placeholderIdx >= 0) {
            const currentSteps = newMessages[placeholderIdx].steps || [];
            newMessages[placeholderIdx] = {
              ...newMessages[placeholderIdx],
              steps: [...currentSteps, errorStep],
            };
          }
          return newMessages;
        });

        setIsLoading(false);

        if (data.reasoning_partial) {
          setIsReasoningStreaming(false);
        }
      } else if (data.type === "reasoning.delta" && data.reasoning) {
        setIsReasoningStreaming(true);
        setCurrentReasoning((prev) => prev + data.reasoning);
        const reasoningStep: ConversationStep = {
          id: generateStepId(),
          type: "reasoning",
          content: data.reasoning || "",
          timestamp: new Date().toISOString(),
          data: { agent_id: data.agent_id },
          category: data.category as ConversationStep["category"],
          uiHint: data.ui_hint
            ? {
                component: data.ui_hint.component,
                priority: data.ui_hint.priority,
                collapsible: data.ui_hint.collapsible,
                iconHint: data.ui_hint.icon_hint,
              }
            : undefined,
        };
        setMessages((prev) => {
          const newMessages = [...prev];
          let placeholderIdx = -1;
          for (let i = newMessages.length - 1; i >= 0; i--) {
            if (newMessages[i].role === "assistant") {
              placeholderIdx = i;
              break;
            }
          }
          if (placeholderIdx >= 0) {
            const currentSteps = newMessages[placeholderIdx].steps || [];
            newMessages[placeholderIdx] = {
              ...newMessages[placeholderIdx],
              steps: [...currentSteps, reasoningStep],
              workflowPhase: "Reasoning...",
            };
          }
          return newMessages;
        });
      } else if (data.type === "reasoning.completed") {
        setIsReasoningStreaming(false);
      } else if (data.type === "done" || data.type === "cancelled") {
        setIsReasoningStreaming(false);
        setCurrentReasoning("");
        setCurrentWorkflowPhase("");
        setCurrentAgent(null);
        setIsLoading(false);
      }
    },
    [],
  );

  const sendMessage = useCallback(
    async (content: string, options?: SendMessageOptions) => {
      if (!content.trim()) return;

      let currentConvId = conversationId;
      if (!currentConvId) {
        try {
          const conv = await api.createConversation("New Chat");
          currentConvId = conv.id;
          setConversationId(conv.id);
        } catch (error) {
          console.error("Failed to create conversation:", error);
          return;
        }
      }

      // Generate a group ID for this conversation turn
      const groupId = `group-${Date.now()}`;
      currentGroupIdRef.current = groupId;

      // OPTIMISTIC UPDATE: Add user message immediately
      const userMessage: Message = {
        id: generateMessageId(),
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };

      // Add placeholder assistant message
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

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsLoading(true);
      setCurrentWorkflowPhase("Starting...");
      accumulatedContentRef.current = "";

      // Close any existing WebSocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      // Create WebSocket connection
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/api/ws/chat`;

      const ws = new ReconnectingWebSocket(wsUrl, [], {
        maxReconnectionDelay: 10000,
        reconnectionDelayGrowFactor: 1.3,
        maxRetries: 3,
      });

      wsRef.current = ws;

      ws.onopen = () => {
        // Send chat request as first message
        const request: ChatRequest = {
          conversation_id: currentConvId!,
          message: content,
          stream: true,
          reasoning_effort: options?.reasoning_effort,
        };
        ws.send(JSON.stringify(request));
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const data: StreamEvent = JSON.parse(event.data as string);
          handleStreamEvent(data, groupId);
        } catch (e) {
          console.error("Error parsing WebSocket message:", e);
        }
      };

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ws.onerror = (error: any) => {
        console.error("WebSocket error:", error);
        // Mark the message as errored
        setMessages((prev) => {
          const newMessages = [...prev];
          const lastMsgIndex = newMessages.length - 1;
          if (newMessages[lastMsgIndex]?.role === "assistant") {
            newMessages[lastMsgIndex] = {
              ...newMessages[lastMsgIndex],
              isWorkflowPlaceholder: false,
              content: "Sorry, something went wrong. Please try again.",
              workflowPhase: undefined,
            };
          }
          return newMessages;
        });
      };

      ws.onclose = () => {
        setIsLoading(false);
        setCurrentWorkflowPhase("");
        setCurrentAgent(null);
        wsRef.current = null;
        accumulatedContentRef.current = "";
      };
    },
    [conversationId, handleStreamEvent],
  );

  return {
    messages,
    isLoading,
    isInitializing,
    currentReasoning,
    isReasoningStreaming,
    currentWorkflowPhase,
    currentAgent,
    sendMessage,
    cancelStreaming,
    conversationId,
    createConversation,
    conversations,
    loadConversations,
    selectConversation,
    isConversationsLoading,
  };
};
