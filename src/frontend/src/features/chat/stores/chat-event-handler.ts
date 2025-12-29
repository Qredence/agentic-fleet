import type { Message, StreamEvent, ConversationStep } from "@/api/types";
import {
  parseVerificationReport,
  formatReportAsSteps,
  isVerificationReport,
} from "@/features/workflow/components/content-parser";
import { getGlobalToastInstance } from "@/hooks/use-toast";
import {
  isDuplicateStep,
  createErrorStep,
  createStatusStep,
  createProgressStep,
  generateStepId,
} from "@/features/workflow/lib";
import { getWorkflowPhase } from "@/features/workflow/lib";
import type { ChatState } from "./types";

// =============================================================================
// Types
// =============================================================================

type ZustandSet = (
  partial: Partial<ChatState> | ((state: ChatState) => Partial<ChatState>),
) => void;

// =============================================================================
// Message Content Tracking
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

export function clearMessageContent(messageId: string | undefined): void {
  if (messageId) messageContentMap.delete(messageId);
}

export function startNewMessage(messageId: string | undefined): void {
  if (messageId) messageContentMap.set(messageId, "");
}

/**
 * Clear all message content entries.
 * Use this during cleanup/reset to prevent memory leaks.
 */
export function clearAllMessageContent(): void {
  messageContentMap.clear();
}

// =============================================================================
// Message Update Helpers
// =============================================================================

/**
 * Helper to update the last assistant message with a transformation function.
 */
export function updateLastAssistantMessage(
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
export function addStepToLastMessage(
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

function lastAssistantHasSteps(state: ChatState): boolean {
  const lastIdx = state.messages.length - 1;
  if (lastIdx < 0) return false;
  const last = state.messages[lastIdx];
  if (!last || last.role !== "assistant") return false;
  return (last.steps?.length ?? 0) > 0;
}

// =============================================================================
// Stream Event Handler
// =============================================================================

export function handleStreamEvent(
  event: StreamEvent,
  set: ZustandSet,
  get: () => ChatState,
  messageId?: string, // Message ID for scoped content tracking
): void {
  // Debug logging for all events (development only)
  if (import.meta.env.DEV) {
    console.debug("[chatStore] Event:", event.type, event.kind || "", {
      message: event.message?.substring(0, 100),
      error: event.error,
      status: event.status,
      workflow_id: event.workflow_id,
      hasData: !!event.data,
      category: event.category,
    });
  }
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
          () => ({
            isWorkflowPlaceholder: false,
            workflow_id:
              event.workflow_id ||
              state.messages[state.messages.length - 1]?.workflow_id,
          }),
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
      set((state) => {
        const withStep = addStepToLastMessage(state, progressStep);
        const withUpdate = updateLastAssistantMessage(
          { ...state, ...withStep },
          () => ({
            workflowPhase: phase,
          }),
        );
        return {
          ...withStep,
          ...withUpdate,
        };
      });
      return;
    }
    // Skip other statuses
    return;
  }

  // Response Delta
  if (event.type === "response.delta" && event.delta) {
    const isResponseCategory =
      event.category === "response" ||
      event.ui_hint?.component === "MessageBubble";
    const logLine = event.log_line?.trim();

    // Detect tool degradation/unavailability warnings (e.g., missing API keys)
    const degradationPattern = /⚠️.*(?:unavailable|disabled|missing.*key)/i;
    if (degradationPattern.test(event.delta)) {
      const toastInstance = getGlobalToastInstance();
      if (toastInstance) {
        // Extract the reason from the message
        const reasonMatch = event.delta.match(/\(([^)]+)\)/);
        const reason = reasonMatch ? reasonMatch[1] : "Configuration issue";
        toastInstance.toast({
          title: "Tool Unavailable",
          description: reason,
          variant: "warning",
          duration: 8000,
        });
      }
    }

    // Always stream response text to the assistant message when the event is a response.
    if (isResponseCategory) {
      const updatedContent = messageId
        ? appendToContent(messageId, event.delta)
        : event.delta;
      set((state) => {
        const withContent = updateLastAssistantMessage(state, () => ({
          content: updatedContent,
          isWorkflowPlaceholder: false,
          workflowPhase: phase,
          workflow_id:
            event.workflow_id ||
            state.messages[state.messages.length - 1]?.workflow_id,
        }));

        // If no trace steps are available yet, surface the backend log line once
        // so Chain of Thought has at least one visible step.
        if (logLine && !lastAssistantHasSteps(state)) {
          const logStep = createStatusStep(
            logLine,
            event.kind ?? "response",
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
          const mergedState = { ...state, ...withContent };
          const withStep = addStepToLastMessage(mergedState, logStep);
          return { ...withContent, ...withStep };
        }

        return withContent;
      });
      return;
    }

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

      set((state) => {
        const withStep = addStepToLastMessage(state, statusStep);
        const withUpdate = updateLastAssistantMessage(
          { ...state, ...withStep },
          () => ({
            workflowPhase: phase,
          }),
        );
        return {
          ...withStep,
          ...withUpdate,
        };
      });
    } else {
      // Direct text delta - use message-scoped tracking to prevent race conditions
      const updatedContent = messageId
        ? appendToContent(messageId, event.delta)
        : event.delta;
      set((state) =>
        updateLastAssistantMessage(state, () => ({
          content: updatedContent,
          isWorkflowPlaceholder: false,
          workflowPhase: phase,
          workflow_id:
            event.workflow_id ||
            state.messages[state.messages.length - 1]?.workflow_id,
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

    // Build richer step content for phase completions
    let stepContent = event.message || "";
    const phaseKind = event.kind;
    const stepData = { ...event.data };

    // Enhance content for specific phase types
    if (event.type === "orchestrator.thought" && phaseKind) {
      if (phaseKind === "analysis" && stepData.complexity) {
        const capabilities = Array.isArray(stepData.capabilities)
          ? stepData.capabilities.slice(0, 3).join(", ")
          : "general reasoning";
        stepContent = `Analysis complete: ${capabilities} (${stepData.complexity} complexity)`;
        if (stepData.steps) {
          stepContent += ` - ${stepData.steps} step(s) required`;
        }
      } else if (phaseKind === "routing" && stepData.assigned_to) {
        const agents = Array.isArray(stepData.assigned_to)
          ? stepData.assigned_to.join(" → ")
          : stepData.assigned_to;
        const mode = stepData.mode || "delegated";
        stepContent = `Routing complete: ${agents} (${mode} mode)`;
        if (stepData.subtasks && Array.isArray(stepData.subtasks)) {
          stepContent += ` - ${stepData.subtasks.length} subtask(s)`;
        }
      } else if (phaseKind === "execution") {
        stepContent = stepContent || "Execution phase complete";
      } else if (phaseKind === "progress") {
        const action = stepData.action || "evaluated";
        stepContent = `Progress assessment: ${action}`;
        if (stepData.feedback) {
          stepContent += ` - ${stepData.feedback}`;
        }
      } else if (phaseKind === "quality") {
        const score = stepData.score ?? 0;
        stepContent = `Quality assessment complete: ${Number(score).toFixed(1)}/10`;
        if (
          stepData.missing &&
          Array.isArray(stepData.missing) &&
          stepData.missing.length > 0
        ) {
          stepContent += ` - ${stepData.missing.length} missing element(s)`;
        }
      }
    }

    const newStep: ConversationStep = {
      id: generateStepId(),
      type: stepType,
      content: stepContent,
      timestamp: new Date().toISOString(),
      kind: phaseKind,
      data: stepData,
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
      event.type === "orchestrator.thought" && phaseKind && phaseMap[phaseKind]
        ? [...new Set([...get().completedPhases, phaseMap[phaseKind]])]
        : get().completedPhases;

    set((state) => {
      const withStep = addStepToLastMessage(state, newStep);
      const withUpdate = updateLastAssistantMessage(
        { ...state, ...withStep },
        () => ({
          workflowPhase: phase,
          completedPhases: newCompletedPhases,
          workflow_id:
            event.workflow_id ||
            state.messages[state.messages.length - 1]?.workflow_id,
        }),
      );

      // Debug: Log step creation for orchestrator events
      if (import.meta.env.DEV) {
        const finalMessages =
          withUpdate.messages || withStep.messages || state.messages;
        const lastMsg = finalMessages[finalMessages.length - 1];
        console.debug(
          "[chatStore] Added orchestrator step:",
          stepType,
          phaseKind,
          "Total steps:",
          lastMsg?.steps?.length || 0,
        );
      }

      return {
        ...withStep,
        ...withUpdate,
        completedPhases: newCompletedPhases,
      };
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

    const agentOutput =
      event.type === "agent.output" || event.type === "agent.message"
        ? event.message || event.content || ""
        : undefined;

    // Check if agent output contains a verification report
    const verificationReport =
      agentOutput &&
      typeof agentOutput === "string" &&
      isVerificationReport(agentOutput)
        ? parseVerificationReport(agentOutput)
        : null;

    if (verificationReport) {
      // Convert verification report to chain-of-thought steps
      const reportSteps = formatReportAsSteps(verificationReport);
      set((state) => {
        let newState = state;
        // Add all report steps to the message
        for (const step of reportSteps) {
          newState = {
            ...newState,
            ...addStepToLastMessage(newState, step, false),
          };
        }
        // Also add a summary step indicating this is a verification report
        const summaryStep: ConversationStep = {
          id: generateStepId(),
          type: "status",
          content: `${agentLabel}: Verification report`,
          timestamp: new Date().toISOString(),
          kind: "verification_report",
          category: "analysis",
          data: {
            agent_id: event.agent_id,
            author: event.author,
            report_sections: reportSteps.length,
          },
        };
        return {
          ...addStepToLastMessage(newState, summaryStep),
          ...updateLastAssistantMessage(newState, () => ({
            workflowPhase: phase,
            workflow_id:
              event.workflow_id ||
              state.messages[state.messages.length - 1]?.workflow_id,
          })),
        };
      });
    } else {
      // Standard agent event handling
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
          output: agentOutput,
        },
        category: event.category as ConversationStep["category"],
      };

      set((state) => ({
        ...addStepToLastMessage(state, newStep),
        ...updateLastAssistantMessage(state, () => ({
          workflowPhase: phase,
          workflow_id:
            event.workflow_id ||
            state.messages[state.messages.length - 1]?.workflow_id,
        })),
      }));
    }
  }

  // Response Completed
  else if (event.type === "response.completed") {
    const finalContent = event.message || "";
    set((state) => {
      const updatedState = updateLastAssistantMessage(state, (msg) => ({
        content: finalContent || msg.content,
        author: finalContent ? "Final Answer" : msg.author,
        isWorkflowPlaceholder: false,
        workflowPhase: "",
        qualityScore: event.quality_score,
        // Preserve existing completedPhases from message, or use state-level tracking
        completedPhases: msg.completedPhases || state.completedPhases,
        workflow_id: event.workflow_id || msg.workflow_id,
      }));

      // Check if final content contains a verification report that wasn't already parsed
      const lastMessage =
        updatedState.messages?.[updatedState.messages.length - 1];
      const contentToCheck = finalContent || lastMessage?.content || "";
      if (
        typeof contentToCheck === "string" &&
        isVerificationReport(contentToCheck) &&
        lastMessage
      ) {
        // Check if we already have verification report steps
        const hasVerificationSteps = lastMessage.steps?.some((s) =>
          s.kind?.startsWith("verification_"),
        );
        if (!hasVerificationSteps) {
          const verificationReport = parseVerificationReport(contentToCheck);
          if (verificationReport) {
            const reportSteps = formatReportAsSteps(verificationReport);
            let newState = updatedState;
            for (const step of reportSteps) {
              newState = {
                ...newState,
                ...addStepToLastMessage(newState as ChatState, step, false),
              };
            }
            return {
              ...newState,
              currentWorkflowPhase: "",
              currentAgent: null,
            };
          }
        }
      }

      return {
        ...updatedState,
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
    const errorMessage = event.error || "Unknown error";
    const toast = getGlobalToastInstance();
    toast?.toast({
      title: "Stream Error",
      description: errorMessage,
      variant: "destructive",
      duration: 7000,
    });
    const errorStep = createErrorStep(errorMessage);
    set((state) => ({
      ...addStepToLastMessage(state, errorStep, false),
      isLoading: false,
      isReasoningStreaming: false,
    }));
  }
}
