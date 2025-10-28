/**
 * Chat Feature Components Barrel Export
 *
 * Centralized exports for all chat-related components:
 * - Main container component
 * - Specialized sub-components
 * - Re-exports for convenient importing
 */

// Main container
export { ChatContainer } from "./ChatContainer";

// Sub-components (can be used independently)
export { ChatMessagesList } from "./ChatMessagesList";
export { ChatStatusBar } from "./ChatStatusBar";
export { ChatSuggestions } from "./ChatSuggestions";
export { ChatPlanDisplay } from "./ChatPlanDisplay";

// Original components (still used)
export * from "./ChatHeader";
export * from "./ChatInput";
export * from "./ChatMessage";

// Remove ChatSidebar export as it doesn't exist in the current structure
// export * from "./ChatSidebar";
