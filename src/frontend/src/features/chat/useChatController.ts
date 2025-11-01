import { useCallback, useEffect, useRef, useState } from "react";
import {
  createConversation,
  getHealth,
  sendChat,
  sendChatStream,
} from "./useChatClient";

export type ChatMessage = {
  id: string | number;
  role: "user" | "assistant" | "system";
  content: string;
  streaming?: boolean;
};

export function useChatController() {
  const [health, setHealth] = useState<"ok" | "down" | "checking">("checking");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    getHealth()
      .then(() => setHealth("ok"))
      .catch(() => setHealth("down"));

    createConversation()
      .then((conv) => {
        console.log("Conversation created:", conv.id);
        setConversationId(conv.id);
        if (conv.messages && conv.messages.length > 0) {
          setMessages(
            conv.messages.map((m, index) => ({
              id: `${conv.id}-${index}`,
              role: m.role as ChatMessage["role"],
              content: m.content,
            })),
          );
        }
      })
      .catch((err) => {
        console.error("Failed to create conversation:", err);
        setError("Failed to create conversation");
      });
  }, []);

  const send = useCallback(
    async (text: string, useStreaming = true) => {
      if (!conversationId) {
        console.warn("[CHAT] Cannot send: no conversationId");
        return;
      }

      const requestStartTime = performance.now();
      console.log(
        `[CHAT] Starting send request at ${new Date().toISOString()}`,
      );
      console.log(
        `[CHAT] Message: "${text.substring(0, 50)}${text.length > 50 ? "..." : ""}"`,
      );
      console.log(`[CHAT] Conversation ID: ${conversationId}`);
      console.log(`[CHAT] Use streaming: ${useStreaming}`);

      setError(null);
      setPending(true);

      // Cancel any ongoing stream
      if (abortControllerRef.current) {
        console.log("[CHAT] Aborting previous stream");
        abortControllerRef.current.abort();
      }

      // Add user message immediately
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: text,
      };

      setMessages((prev) => {
        const updated = [...prev, userMessage];
        console.log(
          `[CHAT] Added user message. Total messages: ${updated.length}`,
        );
        return updated;
      });

      // Create assistant message placeholder for streaming
      const assistantMessageId = `assistant-${Date.now()}`;
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        streaming: true,
      };

      setMessages((prev) => {
        const updated = [...prev, assistantMessage];
        console.log(
          `[CHAT] Added assistant placeholder. Total messages: ${updated.length}`,
        );
        return updated;
      });

      try {
        if (useStreaming) {
          // Use SSE streaming
          let accumulatedContent = "";
          let chunkCount = 0;
          const streamStartTime = performance.now();

          try {
            console.log(
              `[CHAT] Starting stream for conversation: ${conversationId}`,
            );
            console.log(`[CHAT] Making API call to /v1/chat...`);
            const apiCallStart = performance.now();

            for await (const chunk of sendChatStream(
              conversationId,
              text,
              true,
            )) {
              chunkCount++;
              const chunkTime = performance.now();
              accumulatedContent += chunk;

              // Log every 10th chunk or if chunk is substantial
              if (chunkCount % 10 === 1 || chunk.length > 50) {
                console.log(
                  `[CHAT] Chunk #${chunkCount}: "${chunk.substring(0, 30)}${chunk.length > 30 ? "..." : ""}" ` +
                    `(${chunk.length} chars) | Total: ${accumulatedContent.length} chars | ` +
                    `Time since start: ${(chunkTime - streamStartTime).toFixed(2)}ms | ` +
                    `Time since API call: ${(chunkTime - apiCallStart).toFixed(2)}ms`,
                );
              }

              // Update the assistant message with accumulated content
              setMessages((prev) => {
                const updated = prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, content: accumulatedContent, streaming: true }
                    : msg,
                );
                return updated;
              });
            }

            const streamEndTime = performance.now();
            const totalStreamTime = streamEndTime - streamStartTime;
            const totalRequestTime = streamEndTime - requestStartTime;

            // Mark streaming as complete
            console.log(`[CHAT] Stream complete!`);
            console.log(`[CHAT] Total chunks received: ${chunkCount}`);
            console.log(
              `[CHAT] Final content length: ${accumulatedContent.length} chars`,
            );
            console.log(
              `[CHAT] Stream duration: ${totalStreamTime.toFixed(2)}ms (${(totalStreamTime / 1000).toFixed(2)}s)`,
            );
            console.log(
              `[CHAT] Total request duration: ${totalRequestTime.toFixed(2)}ms (${(totalRequestTime / 1000).toFixed(2)}s)`,
            );
            console.log(
              `[CHAT] Final content preview: "${accumulatedContent.substring(0, 100)}${accumulatedContent.length > 100 ? "..." : ""}"`,
            );

            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, streaming: false, content: accumulatedContent }
                  : msg,
              ),
            );

            // Don't refresh from backend - we already have the streamed content
            // The backend has persisted the message during streaming
          } catch (streamError) {
            const errorTime = performance.now();
            const errorDuration = errorTime - requestStartTime;

            // If streaming fails, fall back to non-streaming
            console.error(
              `[CHAT] Streaming failed after ${errorDuration.toFixed(2)}ms:`,
              streamError,
            );
            console.error(
              `[CHAT] Error details:`,
              streamError instanceof Error
                ? {
                    name: streamError.name,
                    message: streamError.message,
                    stack: streamError.stack,
                  }
                : streamError,
            );

            // Remove the placeholder assistant message
            setMessages((prev) =>
              prev.filter((msg) => msg.id !== assistantMessageId),
            );

            // Try non-streaming fallback
            console.log(`[CHAT] Attempting non-streaming fallback...`);
            const fallbackStart = performance.now();
            const res = await sendChat(conversationId, text);
            const fallbackDuration = performance.now() - fallbackStart;
            console.log(
              `[CHAT] Fallback completed in ${fallbackDuration.toFixed(2)}ms`,
            );

            const updated = res.messages.map((m, index) => ({
              id: `${conversationId}-${index}`,
              role: m.role as ChatMessage["role"],
              content: m.content,
            }));
            setMessages(updated);
          }
        } else {
          // Non-streaming mode (fallback)
          console.log(`[CHAT] Using non-streaming mode`);
          const nonStreamStart = performance.now();
          const res = await sendChat(conversationId, text);
          const nonStreamDuration = performance.now() - nonStreamStart;
          console.log(
            `[CHAT] Non-streaming request completed in ${nonStreamDuration.toFixed(2)}ms`,
          );

          const updated = res.messages.map((m, index) => ({
            id: `${conversationId}-${index}`,
            role: m.role as ChatMessage["role"],
            content: m.content,
          }));
          setMessages(updated);
        }
      } catch (err) {
        const errorTime = performance.now();
        const errorDuration = errorTime - requestStartTime;
        console.error(
          `[CHAT] Request failed after ${errorDuration.toFixed(2)}ms:`,
          err,
        );
        setError(err instanceof Error ? err.message : "Failed to send message");
        // Remove the placeholder assistant message on error
        setMessages((prev) =>
          prev.filter((msg) => msg.id !== assistantMessageId),
        );
      } finally {
        const finalTime = performance.now();
        const totalDuration = finalTime - requestStartTime;
        console.log(
          `[CHAT] Request completed. Total duration: ${totalDuration.toFixed(2)}ms (${(totalDuration / 1000).toFixed(2)}s)`,
        );
        setPending(false);
        abortControllerRef.current = null;
      }
    },
    [conversationId],
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return { health, conversationId, messages, pending, error, send };
}
