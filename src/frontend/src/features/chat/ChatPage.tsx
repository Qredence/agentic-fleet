import {
  ChatMessages,
  ChatInputArea,
  ConcurrentErrorAlert,
} from "@/features/chat";
import {
  ChatHeader,
  SidebarLeft,
  RightPanel,
  RightPanelTrigger,
} from "@/features/layout";
import { SidebarInset, SidebarTrigger } from "@/components/ui";
import type { Message as ChatMessage } from "@/api/types";
import { useChatStore } from "@/features/chat/stores";
import { useConversation } from "@/api/hooks";
import { useState, useMemo, useCallback, useEffect } from "react";
import { useShallow } from "zustand/shallow";
import { DEFAULT_CONVERSATION_TITLE } from "@/lib/constants";
import { useParams } from "react-router-dom";
import { ChainOfThoughtTrace } from "@/features/workflow";
import { TracePanel } from "@/features/chat/components/TracePanel";

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
  const { id } = useParams<{ id: string }>();

  // Split state selectors by concern for better performance
  const { messages, isLoading, conversationId } = useChatStore(
    useShallow((state) => ({
      messages: state.messages,
      isLoading: state.isLoading,
      conversationId: state.conversationId,
    })),
  );

  const { selectConversation, reset } = useChatStore(
    useShallow((state) => ({
      selectConversation: state.selectConversation,
      reset: state.reset,
    })),
  );

  // Handle routing-based conversation selection
  useEffect(() => {
    if (id) {
      if (id !== conversationId) {
        void selectConversation(id);
      }
    } else {
      // If no ID in URL but we have one in store, it means we navigated to root
      // We should reset to new chat state unless we just created one (which would have redirected)
      // For now, simple reset if we are at root
      if (conversationId) {
        // reset may be undefined in some test mocks; guard call
        if (typeof reset === "function") {
          reset();
        }
      }
    }
  }, [id, conversationId, selectConversation, reset]);

  // Use React Query for current conversation
  const { data: currentConversation } = useConversation(conversationId);

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

  // Always show trace if there are steps in any message, or if explicitly enabled, or while loading
  const hasStepsInMessages = messages.some(
    (msg) => msg.role === "assistant" && (msg.steps?.length ?? 0) > 0,
  );
  const shouldShowTrace = showTrace || isLoading || hasStepsInMessages;

  const [prompt, setPrompt] = useState("");

  const headerTitle = useMemo(() => {
    return currentConversation?.title?.trim()
      ? currentConversation.title
      : DEFAULT_CONVERSATION_TITLE;
  }, [currentConversation]);

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
        onWorkflowResponse={(requestId: string, payload: unknown) =>
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

      <div className="relative flex-1 overflow-y-auto w-full">
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
  // Right panel state (sidebar is controlled by App.tsx)
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  const { messages, isLoading, sendWorkflowResponse, showRawReasoning } =
    useChatStore(
      useShallow((state) => ({
        messages: state.messages,
        isLoading: state.isLoading,
        sendWorkflowResponse: state.sendWorkflowResponse,
        showRawReasoning: state.showRawReasoning,
      })),
    );

  const latestAssistantMessage = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i]?.role === "assistant") return messages[i];
    }
    return null;
  }, [messages]);

  return (
    <>
      <SidebarLeft />
      <SidebarInset className="flex flex-col h-screen overflow-hidden transition-all duration-200">
        <ChatContent
          rightPanelOpen={rightPanelOpen}
          onRightPanelToggle={setRightPanelOpen}
        />
      </SidebarInset>

      {/* Right Panel - simple CSS-based collapsible panel with floating style */}
      <RightPanel open={rightPanelOpen}>
        <TracePanel
          message={latestAssistantMessage}
          isLoading={isLoading}
          showRawReasoning={showRawReasoning}
          onWorkflowResponse={(requestId, payload) =>
            sendWorkflowResponse(requestId, payload)
          }
        />
      </RightPanel>
    </>
  );
}
