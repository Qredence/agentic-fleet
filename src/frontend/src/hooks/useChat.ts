import { useState, useRef, useCallback } from "react";
import { createParser, type EventSourceMessage } from "eventsource-parser";
import { api } from "../api/client";
import type { Message, StreamEvent, ConversationStep } from "../api/types";

// Generate unique IDs for steps and messages to avoid React key collisions
let stepIdCounter = 0;
let messageIdCounter = 0;
function generateStepId(): string {
  return `step-${Date.now()}-${++stepIdCounter}-${Math.random().toString(36).substring(2, 9)}`;
}
function generateMessageId(): string {
  return `msg-${Date.now()}-${++messageIdCounter}-${Math.random().toString(36).substring(2, 9)}`;
}

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  currentReasoning: string;
  isReasoningStreaming: boolean;
  currentWorkflowPhase: string;
  sendMessage: (content: string) => Promise<void>;
  cancelStreaming: () => void;
  conversationId: string | null;
  createConversation: () => Promise<void>;
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

export const useChat = (): UseChatReturn => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentReasoning, setCurrentReasoning] = useState<string>("");
  const [isReasoningStreaming, setIsReasoningStreaming] = useState(false);
  const [currentWorkflowPhase, setCurrentWorkflowPhase] = useState<string>("");
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentGroupIdRef = useRef<string>("");

  const cancelStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
      setIsReasoningStreaming(false);
      setCurrentWorkflowPhase("");
    }
  }, []);

  const createConversation = useCallback(async () => {
    try {
      const conv = await api.createConversation("New Chat");
      setConversationId(conv.id);
      setMessages([]);
    } catch (error) {
      console.error("Failed to create conversation:", error);
    }
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
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

      // Add user message immediately
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

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsLoading(true);
      setCurrentWorkflowPhase("Starting...");

      try {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        const response = await api.sendMessage({
          conversation_id: currentConvId,
          message: content,
          stream: true,
        });

        if (!response.body) throw new Error("No response body");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantMessageContent = "";

        const parser = createParser({
          onEvent: (event: EventSourceMessage) => {
            try {
              const data: StreamEvent = JSON.parse(event.data);

              // Update workflow phase for shimmer display
              const phase = getWorkflowPhase(data);
              setCurrentWorkflowPhase(phase);

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

                  setMessages((prev) => {
                    const newMessages = [...prev];
                    const lastMsgIndex = newMessages.length - 1;
                    if (newMessages[lastMsgIndex].role === "assistant") {
                      const currentSteps =
                        newMessages[lastMsgIndex].steps || [];
                      newMessages[lastMsgIndex] = {
                        ...newMessages[lastMsgIndex],
                        steps: [...currentSteps, statusStep],
                        workflowPhase: phase,
                      };
                    }
                    return newMessages;
                  });
                } else {
                  // Otherwise, stream into the assistant visible content
                  assistantMessageContent += data.delta;
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    const lastMsgIndex = newMessages.length - 1;
                    if (newMessages[lastMsgIndex].role === "assistant") {
                      newMessages[lastMsgIndex] = {
                        ...newMessages[lastMsgIndex],
                        content: assistantMessageContent,
                        isWorkflowPlaceholder: false,
                      };
                    }
                    return newMessages;
                  });
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

                setMessages((prev) => {
                  const newMessages = [...prev];
                  const lastMsgIndex = newMessages.length - 1;
                  if (newMessages[lastMsgIndex].role === "assistant") {
                    const currentSteps = newMessages[lastMsgIndex].steps || [];
                    newMessages[lastMsgIndex] = {
                      ...newMessages[lastMsgIndex],
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

                  setMessages((prev) => {
                    const newMessages = [...prev];
                    // Find the workflow placeholder message or the last assistant message
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
                      } else {
                        // If there's already content, add the final answer as a new message
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
                    }
                    return newMessages;
                  });
                }
                setCurrentWorkflowPhase("");
              } else if (data.type === "error") {
                console.error("Stream error event:", data.error);
                const errorStep: ConversationStep = {
                  id: generateStepId(),
                  type: "error",
                  content: data.error || "Unknown error",
                  timestamp: new Date().toISOString(),
                };
                setMessages((prev) => {
                  const newMessages = [...prev];
                  const lastMsgIndex = newMessages.length - 1;
                  if (newMessages[lastMsgIndex].role === "assistant") {
                    const currentSteps = newMessages[lastMsgIndex].steps || [];
                    newMessages[lastMsgIndex] = {
                      ...newMessages[lastMsgIndex],
                      steps: [...currentSteps, errorStep],
                    };
                  }
                  return newMessages;
                });
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
                setMessages((prev) => {
                  const newMessages = [...prev];
                  const lastMsgIndex = newMessages.length - 1;
                  if (newMessages[lastMsgIndex].role === "assistant") {
                    const currentSteps = newMessages[lastMsgIndex].steps || [];
                    newMessages[lastMsgIndex] = {
                      ...newMessages[lastMsgIndex],
                      steps: [...currentSteps, reasoningStep],
                      workflowPhase: "Reasoning...",
                    };
                  }
                  return newMessages;
                });
              } else if (data.type === "reasoning.completed") {
                // Reasoning stream finished
                setIsReasoningStreaming(false);
              } else if (data.type === "done") {
                // Stream complete, reset reasoning state
                setIsReasoningStreaming(false);
                setCurrentReasoning("");
                setCurrentWorkflowPhase("");
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
      } catch (error) {
        console.error("Failed to send message:", error);
      } finally {
        setIsLoading(false);
        setCurrentWorkflowPhase("");
        abortControllerRef.current = null;
      }
    },
    [conversationId],
  );

  return {
    messages,
    isLoading,
    currentReasoning,
    isReasoningStreaming,
    currentWorkflowPhase,
    sendMessage,
    cancelStreaming,
    conversationId,
    createConversation,
  };
};
