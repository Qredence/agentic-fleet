import { useState, useRef, useCallback, useEffect } from "react";
import { createParser, type EventSourceMessage } from "eventsource-parser";
import { api } from "../api/client";
import type {
  Message,
  StreamEvent,
  ConversationStep,
  Conversation,
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

// Batched update helper - accumulates updates and flushes on rAF
function createStreamingBatcher(
  onContentUpdate: (content: string) => void,
  onStepsUpdate: (steps: ConversationStep[]) => void,
) {
  let pendingContent = "";
  let pendingSteps: ConversationStep[] = [];
  let rafId: number | null = null;
  let lastFlushTime = 0;
  const minInterval = 16; // ~60fps

  function scheduleFlush() {
    if (rafId !== null) return;

    rafId = requestAnimationFrame(() => {
      doFlush();
      rafId = null;
    });
  }

  function doFlush() {
    if (pendingContent) {
      onContentUpdate(pendingContent);
      pendingContent = "";
    }

    if (pendingSteps.length > 0) {
      onStepsUpdate(pendingSteps);
      pendingSteps = [];
    }

    lastFlushTime = performance.now();
  }

  function flush() {
    const now = performance.now();
    if (now - lastFlushTime < minInterval) {
      scheduleFlush();
      return;
    }
    doFlush();
  }

  return {
    pushContent(content: string) {
      pendingContent += content;
      scheduleFlush();
    },

    pushStep(step: ConversationStep) {
      pendingSteps.push(step);
      scheduleFlush();
    },

    flush,

    // Force flush ignoring rate limiting - for use at stream end
    forceFlush: doFlush,

    reset() {
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      pendingContent = "";
      pendingSteps = [];
    },
  };
}

type StreamingBatcher = ReturnType<typeof createStreamingBatcher>;

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
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentGroupIdRef = useRef<string>("");
  const batcherRef = useRef<StreamingBatcher | null>(null);
  const accumulatedContentRef = useRef<string>("");

  const cancelStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
      setIsReasoningStreaming(false);
      setCurrentWorkflowPhase("");
      setCurrentAgent(null);
      batcherRef.current?.reset();
    }
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
  }, [loadConversations, selectConversation, createConversation]);

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

      // OPTIMISTIC UPDATE: Add user message immediately with pending state
      const userMessage: Message = {
        id: generateMessageId(),
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };

      // Generate a group ID for this conversation turn
      const groupId = `group-${Date.now()}`;
      currentGroupIdRef.current = groupId;

      // Add placeholder assistant message (workflow placeholder)
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

      // Optimistic state update - UI responds immediately
      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsLoading(true);
      setCurrentWorkflowPhase("Starting...");
      accumulatedContentRef.current = "";

      // Initialize streaming batcher for this session
      batcherRef.current = createStreamingBatcher(
        // Content update handler - batched for performance
        (batchedContent) => {
          accumulatedContentRef.current += batchedContent;
          const finalContent = accumulatedContentRef.current;
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastMsgIndex = newMessages.length - 1;
            if (newMessages[lastMsgIndex]?.role === "assistant") {
              newMessages[lastMsgIndex] = {
                ...newMessages[lastMsgIndex],
                content: finalContent,
                isWorkflowPlaceholder: false,
              };
            }
            return newMessages;
          });
        },
        // Steps update handler - batched for performance
        // Steps should go to the workflow placeholder message (the first assistant message after user message)
        (batchedSteps) => {
          setMessages((prev) => {
            const newMessages = [...prev];
            // Find the workflow placeholder message (first assistant message that has isWorkflowPlaceholder or no content yet)
            // We look for the first assistant message after the last user message
            let placeholderIdx = -1;
            for (let i = newMessages.length - 1; i >= 0; i--) {
              if (newMessages[i].role === "user") {
                // Found the user message, check if next is the placeholder
                if (
                  i + 1 < newMessages.length &&
                  newMessages[i + 1].role === "assistant"
                ) {
                  placeholderIdx = i + 1;
                }
                break;
              }
            }

            // Fallback to last assistant if no placeholder found
            if (placeholderIdx === -1) {
              for (let i = newMessages.length - 1; i >= 0; i--) {
                if (newMessages[i].role === "assistant") {
                  placeholderIdx = i;
                  break;
                }
              }
            }

            if (
              placeholderIdx >= 0 &&
              newMessages[placeholderIdx]?.role === "assistant"
            ) {
              const currentSteps = newMessages[placeholderIdx].steps || [];
              newMessages[placeholderIdx] = {
                ...newMessages[placeholderIdx],
                steps: [...currentSteps, ...batchedSteps],
              };
            }
            return newMessages;
          });
        },
      );

      try {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        const response = await api.sendMessage(
          {
            conversation_id: currentConvId,
            message: content,
            stream: true,
            reasoning_effort: options?.reasoning_effort,
          },
          abortControllerRef.current.signal,
        );

        if (!response.body) throw new Error("No response body");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        const parser = createParser({
          onEvent: (event: EventSourceMessage) => {
            try {
              const data: StreamEvent = JSON.parse(event.data);

              // Update workflow phase for shimmer display
              const phase = getWorkflowPhase(data);
              setCurrentWorkflowPhase(phase);

              // Track current agent for typing indicator
              if (data.agent_id || data.author) {
                setCurrentAgent(data.author || data.agent_id || null);
              }

              if (data.type === "response.delta" && data.delta) {
                // If the delta is clearly an execution/handoff status, treat it as a step
                if (data.kind || data.agent_id) {
                  const statusStep: ConversationStep = {
                    id: generateStepId(),
                    type: "status",
                    content: `${data.agent_id ? `${data.agent_id}: ` : ""}${data.delta}`,
                    timestamp: new Date().toISOString(),
                    kind: data.kind,
                    data: data.data,
                  };

                  // Use batched step update
                  batcherRef.current?.pushStep(statusStep);
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    const lastMsgIndex = newMessages.length - 1;
                    if (newMessages[lastMsgIndex].role === "assistant") {
                      newMessages[lastMsgIndex] = {
                        ...newMessages[lastMsgIndex],
                        workflowPhase: phase,
                      };
                    }
                    return newMessages;
                  });
                } else {
                  // Use batched content update for streaming text
                  batcherRef.current?.pushContent(data.delta);
                }
              } else if (
                data.type === "orchestrator.message" ||
                data.type === "orchestrator.thought"
              ) {
                const newStep: ConversationStep = {
                  id: generateStepId(),
                  type:
                    data.type === "orchestrator.thought" ? "thought" : "status",
                  content: data.message || "",
                  timestamp: new Date().toISOString(),
                  kind: data.kind,
                  data: data.data,
                };

                // Use batched step update
                batcherRef.current?.pushStep(newStep);
                setMessages((prev) => {
                  const newMessages = [...prev];
                  const lastMsgIndex = newMessages.length - 1;
                  if (newMessages[lastMsgIndex].role === "assistant") {
                    newMessages[lastMsgIndex] = {
                      ...newMessages[lastMsgIndex],
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

                // For agent.start, agent.complete, and agent.thought - add to workflow events on placeholder
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
                  };

                  // Use batched step update
                  batcherRef.current?.pushStep(newStep);
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    // Find the workflow placeholder message or the last assistant message
                    for (let i = newMessages.length - 1; i >= 0; i--) {
                      if (newMessages[i].role === "assistant") {
                        newMessages[i] = {
                          ...newMessages[i],
                          workflowPhase: phase,
                        };
                        break;
                      }
                    }
                    return newMessages;
                  });
                }

                // For agent.message or agent.output, handle the agent response
                // agent.output events typically contain complete responses and should REPLACE content
                // agent.message events may be incremental and should APPEND content
                if (
                  (data.type === "agent.message" ||
                    data.type === "agent.output") &&
                  (data.message || data.content)
                ) {
                  const agentContent = data.message || data.content || "";
                  const groupId = currentGroupIdRef.current;
                  const isCompleteOutput = data.type === "agent.output";

                  setMessages((prev) => {
                    const newMessages = [...prev];

                    // Check if the last message is a workflow placeholder with no content
                    const lastMsgIndex = newMessages.length - 1;
                    const lastMsg = newMessages[lastMsgIndex];

                    if (
                      lastMsg.role === "assistant" &&
                      lastMsg.isWorkflowPlaceholder &&
                      !lastMsg.content
                    ) {
                      // Update the placeholder with the agent response
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
                      // Different agent responding - create a new message
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
                      // Same agent - append content for incremental messages, replace for complete outputs
                      for (let i = newMessages.length - 1; i >= 0; i--) {
                        if (newMessages[i].role === "assistant") {
                          const existingContent = newMessages[i].content || "";
                          // For agent.output (complete responses), replace content
                          // For agent.message (may be incremental), append with newline separator if there's existing content
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
                    return newMessages;
                  });
                }
              } else if (data.type === "response.completed") {
                // Force flush any pending batched updates before final response
                batcherRef.current?.forceFlush();

                // Final response - this is the synthesized answer to the user's query
                // Always show the final answer as a new message from "Final Answer" or update last empty one
                if (data.message && data.message.trim().length > 0) {
                  const finalContent = data.message;
                  const groupId = currentGroupIdRef.current;

                  setMessages((prev) => {
                    const newMessages = [...prev];

                    // Find the last assistant message
                    let lastAssistantIdx = -1;
                    for (let i = newMessages.length - 1; i >= 0; i--) {
                      if (newMessages[i].role === "assistant") {
                        lastAssistantIdx = i;
                        break;
                      }
                    }

                    if (lastAssistantIdx >= 0) {
                      const lastMsg = newMessages[lastAssistantIdx];
                      // If the last message is empty or a placeholder, update it with final content
                      if (
                        !lastMsg.content ||
                        lastMsg.content.trim().length === 0 ||
                        lastMsg.isWorkflowPlaceholder
                      ) {
                        newMessages[lastAssistantIdx] = {
                          ...lastMsg,
                          content: finalContent,
                          author: "Final Answer",
                          isWorkflowPlaceholder: false,
                          workflowPhase: undefined,
                        };
                      } else if (
                        lastMsg.content.trim() !== finalContent.trim()
                      ) {
                        // Only add new message if content differs from existing
                        const finalAnswerMessage: Message = {
                          id: generateMessageId(),
                          role: "assistant",
                          content: finalContent,
                          created_at: new Date().toISOString(),
                          author: "Final Answer",
                          groupId,
                          isWorkflowPlaceholder: false,
                        };
                        newMessages.push(finalAnswerMessage);
                      }
                      // If content is the same, don't create duplicate message
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
                };
                // Use batched step update for errors too
                batcherRef.current?.pushStep(errorStep);
                batcherRef.current?.forceFlush();

                // If reasoning was interrupted, keep partial reasoning visible
                if (data.reasoning_partial) {
                  setIsReasoningStreaming(false);
                  // Don't clear currentReasoning so user can see partial output
                }
              } else if (data.type === "reasoning.delta" && data.reasoning) {
                // Accumulate reasoning tokens from GPT-5 models
                setIsReasoningStreaming(true);
                setCurrentReasoning((prev) => prev + data.reasoning);
                const reasoningStep: ConversationStep = {
                  id: generateStepId(),
                  type: "reasoning",
                  content: data.reasoning || "",
                  timestamp: new Date().toISOString(),
                  data: { agent_id: data.agent_id },
                };
                // Use batched step update for reasoning
                batcherRef.current?.pushStep(reasoningStep);
                setMessages((prev) => {
                  const newMessages = [...prev];
                  const lastMsgIndex = newMessages.length - 1;
                  if (newMessages[lastMsgIndex].role === "assistant") {
                    newMessages[lastMsgIndex] = {
                      ...newMessages[lastMsgIndex],
                      workflowPhase: "Reasoning...",
                    };
                  }
                  return newMessages;
                });
              } else if (data.type === "reasoning.completed") {
                // Reasoning stream finished
                setIsReasoningStreaming(false);
              } else if (data.type === "done") {
                // Stream complete, force flush any pending batched updates
                batcherRef.current?.forceFlush();
                setIsReasoningStreaming(false);
                setCurrentReasoning("");
                setCurrentWorkflowPhase("");
                setCurrentAgent(null);
              }
            } catch (e) {
              console.error("Error parsing SSE event:", e);
            }
          },
        });

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          parser.feed(decoder.decode(value));
        }

        // Final force flush after stream completes
        batcherRef.current?.forceFlush();
      } catch (error) {
        // Handle user-initiated abort gracefully
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        console.error("Failed to send message:", error);

        // Mark the message as errored for visual feedback
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
      } finally {
        setIsLoading(false);
        setCurrentWorkflowPhase("");
        setCurrentAgent(null);
        abortControllerRef.current = null;
        batcherRef.current?.reset();
        accumulatedContentRef.current = "";
      }
    },
    [conversationId],
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
