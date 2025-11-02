// Chat Feature Components
// Exports all chat-related components for easy importing

// Core Components
export { default as ChatPage } from "./ChatPage";
export { ChatInput } from "./ChatInput";
export { EnhancedMessageList as MessageList } from "./EnhancedMessageList";
export { StreamingMessage } from "./StreamingMessage";

// Basic Components
export { MessageList } from "./MessageList";
export { PromptBar } from "./PromptBar";

// Supporting Components
export { PromptSuggestions } from "./PromptSuggestions";
export { StreamingDashboard } from "./StreamingDashboard";

// Hooks (moved to features/chat)
export { useEnhancedChat } from "./useEnhancedChat";

// Types (if any separate type files are created)
// export type { ChatInputProps } from './ChatInput.types';
// export type { MessageListProps } from './MessageList.types';
