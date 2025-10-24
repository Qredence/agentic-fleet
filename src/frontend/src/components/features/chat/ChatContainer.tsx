import { Plan, PlanContent, PlanHeader, PlanTitle, PlanTrigger } from "@/components/ai/plan";
import { ApprovalPrompt } from "@/components/features/approval";
import { ConnectionStatusIndicator } from "@/components/features/shared";
import { PromptSuggestion } from "@/components/ui/custom/prompt-suggestion";
import { TextShimmer } from "@/components/ui/custom/text-shimmer";
import { Badge } from "@/components/ui/shadcn/badge";
import { Button } from "@/components/ui/shadcn/button";
import { useToast } from "@/hooks/use-toast";
import { mapRoleToAgent } from "@/lib/agent-utils";
import { Message } from "@/lib/types";
import { useFastAPIChat } from "@/lib/use-fastapi-chat";
import logoDark from "@/public/logo-darkmode.svg";
import logoLight from "@/public/logo-lightmode.svg";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowDown, Loader2, Search, Target, TrendingUp } from "lucide-react";
import type { CSSProperties } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChatHeader } from "./ChatHeader";
import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";

const DEFAULT_HEADER_HEIGHT = 64;

interface ChatContainerProps {
  conversationId?: string;
  onConversationChange?: (conversationId?: string) => void;
}

export const ChatContainer = ({
  conversationId: activeConversationId,
  onConversationChange,
}: ChatContainerProps) => {
  type DisplayMessage = Message & { receivedAt: string };

  const [selectedModel, setSelectedModel] = useState<string>("magentic_fleet");
  const [displayMessages, setDisplayMessages] = useState<DisplayMessage[]>([]);
  const {
    messages,
    status,
    error,
    sendMessage,
    pendingApprovals,
    approvalStatuses,
    respondToApproval,
    currentPlan,
    conversationId,
    queueStatus,
    connectionStatus,
    checkHealth,
  } = useFastAPIChat({ model: selectedModel, conversationId: activeConversationId });

  const queryClient = useQueryClient();
  const { toast } = useToast();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messageTimestampsRef = useRef<Map<string, string>>(new Map());
  const hasHydratedRef = useRef(false);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [isDarkMode, setIsDarkMode] = useState(false);

  const timeFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      }),
    []
  );

  const scrollToLatest = useCallback(() => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
          setIsAtBottom(true);
        }
      });
    });
  }, []);

  const handleScroll = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }

    const threshold = 120;
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    setIsAtBottom(distanceFromBottom <= threshold);
  }, []);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }

    container.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => {
      container.removeEventListener("scroll", handleScroll);
    };
  }, [handleScroll]);

  useEffect(() => {
    if (typeof document === "undefined") {
      return;
    }

    const updateTheme = () => {
      setIsDarkMode(document.documentElement.classList.contains("dark"));
    };

    updateTheme();

    let observer: MutationObserver | null = null;

    if (typeof MutationObserver !== "undefined") {
      observer = new MutationObserver(updateTheme);
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    }

    return () => {
      observer?.disconnect();
    };
  }, []);

  // Handle display message updates and scroll
  useEffect(() => {
    const nowISO = new Date().toISOString();

    const nextDisplayMessages = messages.map((msg) => {
      const existingTimestamp = messageTimestampsRef.current.get(msg.id);

      if (!existingTimestamp) {
        messageTimestampsRef.current.set(msg.id, nowISO);
      }

      const receivedAt = messageTimestampsRef.current.get(msg.id) ?? nowISO;
      const isExisting = Boolean(existingTimestamp);

      return {
        ...msg,
        receivedAt,
        isNew: msg.isNew ?? (hasHydratedRef.current ? !isExisting : false),
      };
    });

    setDisplayMessages(nextDisplayMessages);

    const lastMessage = messages[messages.length - 1];
    const shouldAutoScroll = isAtBottom || lastMessage?.role === "user";
    if (shouldAutoScroll && nextDisplayMessages.length > 0) {
      scrollToLatest();
    }

    if (!hasHydratedRef.current) {
      hasHydratedRef.current = true;
      return;
    }

    const timeout = setTimeout(() => {
      setDisplayMessages((prev) => prev.map((msg) => ({ ...msg, isNew: false })));
    }, 300);

    return () => {
      clearTimeout(timeout);
    };
  }, [messages, isAtBottom, scrollToLatest]);

  const handleSendMessage = useCallback(
    async (message: string) => {
      scrollToLatest();
      await sendMessage(message);
    },
    [sendMessage, scrollToLatest]
  );

  const handleApprove = useCallback(
    async (
      requestId: string,
      options?: { modifiedCode?: string; modifiedParams?: Record<string, unknown>; reason?: string }
    ) => {
      try {
        await respondToApproval(requestId, {
          decision: options?.modifiedCode ? "modified" : "approved",
          modifiedCode: options?.modifiedCode,
          reason: options?.reason,
        });
        toast({ title: "Approval submitted" });
      } catch (err) {
        toast({
          title: "Approval failed",
          description: err instanceof Error ? err.message : "Unable to submit approval",
          variant: "destructive",
        });
      }
    },
    [respondToApproval, toast]
  );

  const handleReject = useCallback(
    async (requestId: string, reason: string) => {
      try {
        await respondToApproval(requestId, {
          decision: "rejected",
          reason,
        });
        toast({ title: "Request rejected" });
      } catch (err) {
        toast({
          title: "Rejection failed",
          description: err instanceof Error ? err.message : "Unable to reject request",
          variant: "destructive",
        });
      }
    },
    [respondToApproval, toast]
  );

  const handleSelectConversation = useCallback(
    (conversationId?: string) => {
      onConversationChange?.(conversationId);
    },
    [onConversationChange]
  );

  useEffect(() => {
    if (onConversationChange) {
      onConversationChange(conversationId);
    }
  }, [conversationId, onConversationChange]);

  useEffect(() => {
    if (conversationId) {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    }
  }, [conversationId, queryClient]);

  const queueSummary = useMemo(() => {
    if (!queueStatus) {
      return null;
    }
    const { queued, inflight, maxParallel, phase } = queueStatus;
    if (queued === 0 && inflight === 0) {
      return null;
    }
    const normalizedPhase = phase && phase.length > 0 ? phase : "queued";
    const phaseLabel =
      normalizedPhase.charAt(0).toUpperCase() + normalizedPhase.slice(1).toLowerCase();
    return `${phaseLabel}: ${inflight}/${maxParallel} running · ${queued} waiting`;
  }, [queueStatus]);

  const isProcessing = useMemo(() => status === "streaming" || status === "submitted", [status]);
  const showScrollToLatest = !isAtBottom && displayMessages.length > 0;

  const statusLabel = useMemo(() => {
    switch (status) {
      case "streaming":
        return "Agents responding";
      case "submitted":
        return "Queued for orchestration";
      case "error":
        return "Encountered an error";
      default:
        return "Ready";
    }
  }, [status]);

  const selectedWorkflowLabel =
    selectedModel === "magentic_fleet" ? "Magentic Fleet" : "Reflection & Retry";

  const contentStyle = useMemo<CSSProperties>(() => {
    return {
      paddingTop: DEFAULT_HEADER_HEIGHT,
      height: "100vh",
    };
  }, []);

  const logoSrc = isDarkMode ? logoDark : logoLight;

  return (
    <div className="flex w-full flex-col bg-background" style={{ height: "100vh" }}>
      {/* Top Navigation */}
      <ChatHeader
        logoSrc={logoSrc}
        statusLabel={statusLabel}
        selectedWorkflowLabel={selectedWorkflowLabel}
        selectedModel={selectedModel}
        activeConversationId={activeConversationId}
        onModelChange={setSelectedModel}
        onSelectConversation={handleSelectConversation}
      />

      <div className="flex w-full flex-1" style={contentStyle}>
        <div className="mx-auto flex w-full max-w-[800px] flex-1 flex-col pb-32">
          {queueSummary && (
            <div className="px-6 pt-2">
              <Badge
                variant="secondary"
                className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-background/70 px-3 py-1 text-xs font-medium backdrop-blur"
              >
                <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
                {queueSummary}
              </Badge>
            </div>
          )}

          {/* Messages */}
          <div className="relative flex-1 overflow-hidden">
            <div
              ref={messagesContainerRef}
              className="h-full overflow-y-auto px-4 pb-6 pt-4 space-y-3"
              aria-live="polite"
            >
              {displayMessages.length === 0 && (
                <div className="text-center text-muted-foreground py-8">
                  <p className="text-sm">Start a conversation with the agents</p>
                </div>
              )}

              {displayMessages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg.content}
                  agent={mapRoleToAgent(msg.role, msg.actor)}
                  timestamp={timeFormatter.format(new Date(msg.receivedAt))}
                  isNew={msg.isNew}
                  isStreaming={msg.isStreaming}
                />
              ))}

              {/* Current Plan */}
              {currentPlan && (
                <div className="py-4">
                  <Plan isStreaming={currentPlan.isStreaming} defaultOpen>
                    <PlanHeader>
                      <div className="flex-1">
                        <PlanTitle>{currentPlan.title}</PlanTitle>
                        {currentPlan.description && (
                          <p className="text-sm text-muted-foreground mt-1">
                            {currentPlan.description}
                          </p>
                        )}
                      </div>
                      <PlanTrigger />
                    </PlanHeader>
                    <PlanContent>
                      <div className="space-y-2">
                        {currentPlan.steps.map((step, idx) => (
                          <div
                            key={idx}
                            className="flex gap-3 text-sm p-2 rounded-md hover:bg-muted/30 transition-colors"
                          >
                            <span className="text-muted-foreground font-medium min-w-fit">
                              {idx + 1}.
                            </span>
                            <span className="text-foreground">{step}</span>
                          </div>
                        ))}
                      </div>
                    </PlanContent>
                  </Plan>
                </div>
              )}

              {/* Pending Approvals */}
              {pendingApprovals.map((approval) => (
                <div key={approval.requestId} className="py-2">
                  <ApprovalPrompt
                    requestId={approval.requestId}
                    functionCall={approval.functionCall}
                    operation={approval.operation ?? approval.operationType}
                    details={approval.details}
                    code={approval.code}
                    status={approvalStatuses[approval.requestId] || { status: "idle" }}
                    onApprove={(options) => handleApprove(approval.requestId, options)}
                    onReject={(reason) => handleReject(approval.requestId, reason)}
                  />
                </div>
              ))}

              {isProcessing && (
                <div className="flex items-center gap-2 p-4 animate-fade-in">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <TextShimmer className="text-sm" duration={1.5}>
                    Agents are responding...
                  </TextShimmer>
                </div>
              )}

              {error && (
                <div className="p-4 bg-destructive/10 text-destructive rounded-md text-sm">
                  <strong>Error:</strong> {error.message}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {showScrollToLatest && (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                className="absolute bottom-24 right-6 shadow-md rounded-full"
                onClick={scrollToLatest}
              >
                <ArrowDown className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
            )}
          </div>

          {/* Input - Floating at bottom */}
          <div
            className="fixed bottom-[24px] left-0 right-0 z-10 px-4"
            style={{ height: "auto", flexGrow: 0 }}
          >
            <div className="mx-auto max-w-[800px]">
              {/* Prompt Suggestions - only show when no messages */}
              {displayMessages.length === 0 && (
                <div className="flex flex-wrap justify-center items-center gap-2 py-2">
                  <PromptSuggestion
                    icon={<TrendingUp className="h-4 w-4" />}
                    onClick={() => handleSendMessage("Analyze quarterly performance")}
                  >
                    Analyze quarterly performance
                  </PromptSuggestion>
                  <PromptSuggestion
                    icon={<Search className="h-4 w-4" />}
                    onClick={() => handleSendMessage("Research industry trends")}
                  >
                    Research industry trends
                  </PromptSuggestion>
                  <PromptSuggestion
                    icon={<Target className="h-4 w-4" />}
                    onClick={() => handleSendMessage("Create strategic roadmap")}
                  >
                    Create strategic roadmap
                  </PromptSuggestion>
                </div>
              )}
              <ChatInput onSendMessage={handleSendMessage} disabled={isProcessing} />
              <ConnectionStatusIndicator status={connectionStatus} onRetry={checkHealth} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
