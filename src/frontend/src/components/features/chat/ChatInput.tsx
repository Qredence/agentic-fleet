import React, { useState } from "react";
import { EnhancedInput } from "./EnhancedInput";
import { useEnhancedChat } from "./useEnhancedChat";
import type { ProcessedFile } from "@/utils/fileHandling";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// Icons
const PlayIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <polygon points="5 3 19 12 5 21 5 3" fill="currentColor" />
  </svg>
);

const PauseIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <rect x="6" y="4" width="4" height="16" fill="currentColor" />
    <rect x="14" y="4" width="4" height="16" fill="currentColor" />
  </svg>
);

const StopIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <rect x="6" y="6" width="12" height="12" fill="currentColor" />
  </svg>
);

const RefreshIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...props}>
    <path
      d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

interface ChatInputProps {
  className?: string;
  disabled?: boolean;
  placeholder?: string;
  onMessageSent?: (messageId: string) => void;
  onError?: (error: Error) => void;
  showStreamingControls?: boolean;
  enableVoiceInput?: boolean;
  enableFileUpload?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = React.memo(
  ({
    className,
    disabled = false,
    placeholder = "Type your message...",
    onMessageSent,
    onError,
    showStreamingControls = true,
    enableVoiceInput = true,
    enableFileUpload = true,
  }) => {
    const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);

    // Enhanced chat hook
    const {
      state,
      sendMessage,
      pauseStreaming,
      resumeStreaming,
      stopStreaming,
      clearError,
    } = useEnhancedChat({
      onError: (error) => {
        toast.error(error.message);
        onError?.(error);
      },
      onSuccess: (message) => {
        onMessageSent?.(message.id);
        toast.success("Message sent successfully");
      },
    });

    // Handle message sending
    const handleSendMessage = async (
      content: string,
      attachments: ProcessedFile[] = [],
      tools: string[] = [],
      voiceData?: any,
    ) => {
      try {
        await sendMessage(content, attachments, tools, voiceData);
      } catch (error) {
        console.error("Failed to send message:", error);
      }
    };

    // Handle streaming controls
    const handlePauseStreaming = async () => {
      try {
        await pauseStreaming();
        toast.info("Streaming paused");
      } catch (error) {
        console.error("Failed to pause streaming:", error);
        toast.error("Failed to pause streaming");
      }
    };

    const handleResumeStreaming = async () => {
      try {
        await resumeStreaming();
        toast.info("Streaming resumed");
      } catch (error) {
        console.error("Failed to resume streaming:", error);
        toast.error("Failed to resume streaming");
      }
    };

    const handleStopStreaming = async () => {
      try {
        await stopStreaming();
        toast.info("Streaming stopped");
      } catch (error) {
        console.error("Failed to stop streaming:", error);
        toast.error("Failed to stop streaming");
      }
    };

    // Streaming progress calculation
    const streamingProgress = state.streamingProgress.progress || 0;
    const streamingEta = state.streamingProgress.eta;

    return (
      <div className={cn("space-y-4", className)}>
        {/* Error display */}
        {state.error && (
          <Alert variant="destructive">
            <AlertDescription className="flex items-center justify-between">
              <span>{state.error}</span>
              <Button size="sm" variant="ghost" onClick={clearError}>
                Dismiss
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Streaming controls and progress */}
        {showStreamingControls && state.isStreaming && (
          <div className="space-y-3">
            {/* Streaming progress bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="font-medium">
                    {state.streamingProgress.agentName || "Assistant"} is
                    responding...
                  </span>
                </div>
                {streamingEta !== null && (
                  <span className="text-muted-foreground">
                    ~{Math.ceil(streamingEta)}s remaining
                  </span>
                )}
              </div>
              <Progress value={streamingProgress} className="h-2" />
            </div>

            {/* Streaming control buttons */}
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1">
                {state.canPauseStream && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handlePauseStreaming}
                    className="h-8 px-3"
                  >
                    <PauseIcon className="w-3 h-3 mr-1" />
                    Pause
                  </Button>
                )}

                {state.canResumeStream && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleResumeStreaming}
                    className="h-8 px-3"
                  >
                    <PlayIcon className="w-3 h-3 mr-1" />
                    Resume
                  </Button>
                )}

                {state.isStreaming && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleStopStreaming}
                    className="h-8 px-3"
                  >
                    <StopIcon className="w-3 h-3 mr-1" />
                    Stop
                  </Button>
                )}
              </div>

              <div className="ml-auto flex items-center gap-2">
                <Badge variant="secondary" className="text-xs">
                  {streamingProgress.toFixed(0)}% Complete
                </Badge>
              </div>
            </div>
          </div>
        )}

        {/* Main input component */}
        <EnhancedInput
          disabled={disabled || state.isLoading || state.isStreaming}
          onSend={handleSendMessage}
          placeholder={
            state.isStreaming ? "Streaming in progress..." : placeholder
          }
          className={cn(
            state.isStreaming && "opacity-75",
            "transition-all duration-200",
          )}
        />

        {/* Advanced options toggle */}
        <div className="flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
            className="text-muted-foreground"
          >
            {showAdvancedOptions ? "Hide" : "Show"} Advanced Options
          </Button>

          {/* Status indicators */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {state.isLoading && (
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                Sending...
              </div>
            )}
            {state.isStreaming && (
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                Streaming...
              </div>
            )}
          </div>
        </div>

        {/* Advanced options panel */}
        {showAdvancedOptions && (
          <div className="p-4 bg-muted/30 rounded-lg space-y-4">
            <h4 className="text-sm font-medium">Advanced Options</h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Performance metrics */}
              <div className="space-y-2">
                <h5 className="text-xs font-medium text-muted-foreground">
                  Performance
                </h5>
                <div className="text-xs space-y-1">
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <Badge
                      variant={state.error ? "destructive" : "secondary"}
                      className="text-xs"
                    >
                      {state.error
                        ? "Error"
                        : state.isLoading
                          ? "Loading"
                          : state.isStreaming
                            ? "Streaming"
                            : "Ready"}
                    </Badge>
                  </div>
                  {state.streamingProgress.progress > 0 && (
                    <>
                      <div className="flex justify-between">
                        <span>Progress:</span>
                        <span>
                          {state.streamingProgress.progress.toFixed(1)}%
                        </span>
                      </div>
                      {streamingEta !== null && (
                        <div className="flex justify-between">
                          <span>ETA:</span>
                          <span>{Math.ceil(streamingEta)}s</span>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* Feature toggles */}
              <div className="space-y-2">
                <h5 className="text-xs font-medium text-muted-foreground">
                  Features
                </h5>
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={enableVoiceInput}
                      disabled
                      className="rounded"
                    />
                    Voice Input {enableVoiceInput ? "✓" : "✗"}
                  </label>
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={enableFileUpload}
                      disabled
                      className="rounded"
                    />
                    File Upload {enableFileUpload ? "✓" : "✗"}
                  </label>
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={showStreamingControls}
                      disabled
                      className="rounded"
                    />
                    Streaming Controls {showStreamingControls ? "✓" : "✗"}
                  </label>
                </div>
              </div>
            </div>

            {/* Debug info */}
            <div className="pt-2 border-t">
              <details className="text-xs">
                <summary className="cursor-pointer font-medium text-muted-foreground">
                  Debug Information
                </summary>
                <div className="mt-2 space-y-1 font-mono bg-background p-2 rounded border">
                  <div>
                    Conversation ID: {state.currentConversationId || "None"}
                  </div>
                  <div>Message Count: {state.messages.length}</div>
                  <div>Is Loading: {state.isLoading.toString()}</div>
                  <div>Is Streaming: {state.isStreaming.toString()}</div>
                  <div>Can Pause: {state.canPauseStream.toString()}</div>
                  <div>Can Resume: {state.canResumeStream.toString()}</div>
                  {state.error && <div>Error: {state.error}</div>}
                </div>
              </details>
            </div>
          </div>
        )}
      </div>
    );
  },
);

ChatInput.displayName = "ChatInput";
