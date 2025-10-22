import {
  Plan,
  PlanContent,
  PlanHeader,
  PlanTitle,
  PlanTrigger,
} from "@/components/ai-elements/plan";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { PromptSuggestion, PromptSuggestions } from "@/components/ui/prompt-suggestion";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TextShimmer } from "@/components/ui/text-shimmer";
import { useToast } from "@/hooks/use-toast";
import { mapRoleToAgent } from "@/lib/agent-utils";
import { Message } from "@/lib/types";
import { useFastAPIChat } from "@/lib/use-fastapi-chat";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Search, Target, TrendingUp } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApprovalPrompt } from "./ApprovalPrompt";
import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";
import { ConnectionStatusIndicator } from "./ConnectionStatusIndicator";

interface ChatContainerProps {
  conversationId?: string;
  onConversationChange?: (conversationId?: string) => void;
}

export const ChatContainer = ({
  conversationId: activeConversationId,
  onConversationChange,
}: ChatContainerProps) => {
  const [selectedModel, setSelectedModel] = useState<string>("magentic_fleet");
  const [displayMessages, setDisplayMessages] = useState<Message[]>([]);
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

  const scrollToBottom = useCallback(() => {
    // Use double requestAnimationFrame to ensure layout is complete
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
        }
      });
    });
  }, []);

  // Handle display message updates and scroll
  useEffect(() => {
    setDisplayMessages(messages);
    scrollToBottom();

    // Reset isNew flag after animation duration (300ms)
    const timeout = setTimeout(() => {
      setDisplayMessages((prev) => prev.map((msg) => ({ ...msg, isNew: false })));
    }, 300);

    return () => {
      clearTimeout(timeout);
    };
  }, [messages, scrollToBottom]);

  const handleSendMessage = useCallback(
    async (message: string) => {
      await sendMessage(message);
    },
    [sendMessage]
  );

  const handleApprove = useCallback(
    async (requestId: string, options?: { modifiedCode?: string; reason?: string }) => {
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

  return (
    <div className="flex flex-col h-full w-full">
      {/* Header */}
      <div className="border-b border-border/50 p-4 backdrop-blur-sm bg-background/80 space-y-3">
        <div>
          <h2 className="text-lg font-semibold text-foreground">AgenticFleet</h2>
          <p className="text-sm text-muted-foreground">
            {status === "streaming" ? "Agents responding..." : "Ready"}
          </p>
          {queueSummary && (
            <Badge variant="secondary" className="text-xs font-medium mt-2">
              {queueSummary}
            </Badge>
          )}
        </div>

        {/* Model Selection */}
        <div className="flex items-center gap-2">
          <Label htmlFor="model-select" className="text-xs text-muted-foreground">
            Workflow:
          </Label>
          <Select value={selectedModel} onValueChange={setSelectedModel}>
            <SelectTrigger id="model-select" className="h-8 text-xs w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="magentic_fleet">Magentic Fleet</SelectItem>
              <SelectItem value="workflow_as_agent">Reflection & Retry</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Connection Status Indicator */}
      <div className="px-4 pt-4">
        <ConnectionStatusIndicator status={connectionStatus} onRetry={checkHealth} />
      </div>

      {/* Messages */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-4 space-y-1">
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
            timestamp={new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
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
                    <p className="text-sm text-muted-foreground mt-1">{currentPlan.description}</p>
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
              operationType={approval.operationType}
              operation={approval.operation}
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

      {/* Prompt Suggestions - only show when no messages */}
      {displayMessages.length === 0 && (
        <div className="px-4 border-t border-border/50">
          <PromptSuggestions>
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
          </PromptSuggestions>
        </div>
      )}

      {/* Input */}
      <ChatInput onSendMessage={handleSendMessage} disabled={isProcessing} />
    </div>
  );
};
