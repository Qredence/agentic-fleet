// Chat Feature Hooks and Utilities
// Exports all chat-related hooks and utilities for easy importing

// Hooks
export { useChatController } from "./useChatController";
export { useChatClient } from "./useChatClient";

// Types
export type { ChatMessage } from "./useChatController";

// Re-export enhanced hook from components for convenience
export { useEnhancedChat } from "../components/features/chat/useEnhancedChat";
