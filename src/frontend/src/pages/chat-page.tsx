import { ChainOfThoughtTrace } from "@/components/workflow";
import {
  ChatMessages,
  ChatInputArea,
  ConcurrentErrorAlert,
} from "@/components/chat";
import {
  ChatHeader,
  SidebarLeft,
  RightPanel,
  RightPanelTrigger,
} from "@/components/layout";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui";
import type { Message as ChatMessage } from "@/api/types";
import { useChatStore } from "@/stores";
import { useState, useMemo, useCallback } from "react";
import { useShallow } from "zustand/shallow";
import { DEFAULT_CONVERSATION_TITLE } from "@/lib/constants";

/**
 * ChatContent - The main chat interface component
 * Contains message display, input, and trace controls
 */
function ChatContent({
  rightPanelOpen,
  onRightPanelToggle,
}: {
  rightPanelOpen: boolean;
  onRightPanelToggle: (open: boolean) => void;
}) {
  // Split state selectors by concern for better performance
  const { messages, isLoading, conversationId, conversations } = useChatStore(
    useShallow((state) => ({
      messages: state.messages,
      isLoading: state.isLoading,
      conversationId: state.conversationId,
      conversations: state.conversations,
    })),
  );

  const { sendMessage, cancelStreaming, sendWorkflowResponse } = useChatStore(
    useShallow((state) => ({
      sendMessage: state.sendMessage,
      cancelStreaming: state.cancelStreaming,
      sendWorkflowResponse: state.sendWorkflowResponse,
    })),
  );

  const {
    showTrace,
    showRawReasoning,
    executionMode,
    enableGepa,
    isConcurrentError,
    setShowTrace,
    setShowRawReasoning,
    setExecutionMode,
    setEnableGepa,
  } = useChatStore(
    useShallow((state) => ({
      showTrace: state.showTrace,
      showRawReasoning: state.showRawReasoning,
      executionMode: state.executionMode,
      enableGepa: state.enableGepa,
      isConcurrentError: state.isConcurrentError,
      setShowTrace: state.setShowTrace,
      setShowRawReasoning: state.setShowRawReasoning,
      setExecutionMode: state.setExecutionMode,
      setEnableGepa: state.setEnableGepa,
    })),
  );

  const shouldShowTrace = showTrace || isLoading;

  const [prompt, setPrompt] = useState("");

  const headerTitle = useMemo(() => {
    const current = conversations.find((c) => c.id === conversationId);
    return current?.title?.trim() ? current.title : DEFAULT_CONVERSATION_TITLE;
  }, [conversations, conversationId]);

  const handleSubmit = useCallback(() => {
    const text = prompt.trim();
    if (!text || isLoading) return;
    setPrompt("");
    void sendMessage(text);
  }, [prompt, isLoading, sendMessage]);

  const handleToggleGepa = useCallback(() => {
    setEnableGepa(!enableGepa);
  }, [enableGepa, setEnableGepa]);

  const handleToggleTrace = useCallback(() => {
    setShowTrace(!showTrace);
  }, [showTrace, setShowTrace]);

  const handleToggleRawReasoning = useCallback(() => {
    setShowRawReasoning(!showRawReasoning);
  }, [showRawReasoning, setShowRawReasoning]);

  const renderTraceContent = useCallback(
    (message: ChatMessage, isStreaming: boolean) => (
      <ChainOfThoughtTrace
        message={message}
        isStreaming={isStreaming}
        isLoading={isLoading}
        showRawReasoning={showRawReasoning}
        onWorkflowResponse={(requestId, payload) =>
          sendWorkflowResponse(requestId, payload)
        }
      />
    ),
    [isLoading, showRawReasoning, sendWorkflowResponse],
  );

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <ChatHeader
        title={headerTitle}
        sidebarTrigger={<SidebarTrigger />}
        actions={
          <RightPanelTrigger
            open={rightPanelOpen}
            onOpenChange={onRightPanelToggle}
          />
        }
      />

      {isConcurrentError && (
        <ConcurrentErrorAlert onTerminate={cancelStreaming} />
      )}

      <div className="relative flex-1 overflow-y-auto">
        <ChatMessages
          messages={messages}
          isLoading={isLoading}
          renderTrace={shouldShowTrace ? renderTraceContent : undefined}
        />
      </div>

      <ChatInputArea
        isLoading={isLoading}
        prompt={prompt}
        onPromptChange={setPrompt}
        onSubmit={handleSubmit}
        onCancel={cancelStreaming}
        executionMode={executionMode}
        enableGepa={enableGepa}
        showTrace={showTrace}
        showRawReasoning={showRawReasoning}
        onExecutionModeChange={setExecutionMode}
        onToggleGepa={handleToggleGepa}
        onToggleTrace={handleToggleTrace}
        onToggleRawReasoning={handleToggleRawReasoning}
      />
    </div>
  );
}

/**
 * ChatPage - Main page component for the chat interface
 *
 * Uses controlled state for both sidebars:
 * - Left sidebar: Uses SidebarProvider with open/onOpenChange for controlled state
 * - Right panel: Uses simple CSS-based collapsible panel
 *
 * The main content area automatically adapts its width based on which panels are open.
 */
export function ChatPage() {
  // Controlled state for both panels
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  const { messages, isLoading, sendWorkflowResponse } = useChatStore(
    useShallow((state) => ({
      messages: state.messages,
      isLoading: state.isLoading,
      sendWorkflowResponse: state.sendWorkflowResponse,
    })),
  );

  const latestAssistantMessage = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i]?.role === "assistant") return messages[i];
    }
    return null;
  }, [messages]);

  return (
    <SidebarProvider open={leftSidebarOpen} onOpenChange={setLeftSidebarOpen}>
      <SidebarLeft />
      <SidebarInset className="flex flex-col h-screen overflow-hidden transition-all duration-200">
        <ChatContent
          rightPanelOpen={rightPanelOpen}
          onRightPanelToggle={setRightPanelOpen}
        />
      </SidebarInset>

      {/* Right Panel - simple CSS-based collapsible panel with floating style */}
      <RightPanel open={rightPanelOpen} onOpenChange={setRightPanelOpen}>
        <div className="flex h-full flex-col gap-3 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">Chain of Thought</h3>
            <span className="text-xs text-muted-foreground">
              {isLoading ? "Streaming" : "Idle"}
            </span>
          </div>

          {latestAssistantMessage ? (
            <ChainOfThoughtTrace
              message={latestAssistantMessage}
              isStreaming={isLoading}
              isLoading={isLoading}
              showRawReasoning={true}
              onWorkflowResponse={(requestId, payload) =>
                sendWorkflowResponse(requestId, payload)
              }
            />
          ) : (
            <p className="text-sm text-muted-foreground">
              No workflow events yet.
            </p>
          )}
        </div>
      </RightPanel>
    </SidebarProvider>
  );
}
