import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  MessageSquare,
  Search,
  Grid,
  Settings,
} from "lucide-react";
import { clsx } from "clsx";
import type { Conversation } from "../api/types";
import { ConversationListSkeleton } from "./MessageSkeleton";

interface SidebarProps {
  onNewChat?: () => void;
  conversations?: Conversation[];
  currentConversationId?: string | null;
  onSelectConversation?: (id: string) => void;
  isLoading?: boolean;
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return "Today";
  } else if (diffDays === 1) {
    return "Yesterday";
  } else if (diffDays < 7) {
    return `${diffDays} days ago`;
  } else {
    return date.toLocaleDateString();
  }
}

function getConversationTitle(conv: Conversation): string {
  if (conv.title && conv.title !== "New Chat") {
    return conv.title;
  }
  // Try to get first user message as title
  const firstUserMsg = conv.messages?.find((m) => m.role === "user");
  if (firstUserMsg?.content) {
    return (
      firstUserMsg.content.slice(0, 50) +
      (firstUserMsg.content.length > 50 ? "..." : "")
    );
  }
  return conv.title || "New Chat";
}

export const Sidebar: React.FC<SidebarProps> = ({
  onNewChat,
  conversations = [],
  currentConversationId,
  onSelectConversation,
  isLoading = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Animation variants for sidebar
  const sidebarVariants = {
    expanded: { width: 260 },
    collapsed: { width: 64 },
  };

  // Animation variants for conversation items
  const itemVariants = {
    hidden: { opacity: 0, x: -10 },
    visible: (i: number) => ({
      opacity: 1,
      x: 0,
      transition: {
        delay: i * 0.03,
        duration: 0.2,
      },
    }),
    exit: { opacity: 0, x: -10, transition: { duration: 0.15 } },
  };

  return (
    <motion.div
      initial={false}
      animate={isCollapsed ? "collapsed" : "expanded"}
      variants={sidebarVariants}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="h-screen bg-gray-1000 border-r border-gray-800 flex flex-col overflow-hidden"
    >
      <div className="p-3 flex items-center justify-between">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors"
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? (
            <PanelLeftOpen size={20} />
          ) : (
            <PanelLeftClose size={20} />
          )}
        </button>
        {!isCollapsed && (
          <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors">
            <Search size={20} />
          </button>
        )}
      </div>

      <div className="px-3 py-2">
        <button
          onClick={onNewChat}
          className={clsx(
            "flex items-center gap-2 w-full p-2 text-gray-100 hover:bg-gray-800 rounded-md transition-colors border border-gray-800",
            isCollapsed ? "justify-center" : "justify-start",
          )}
          aria-label="Start new chat"
        >
          <Plus size={16} />
          {!isCollapsed && (
            <span className="text-sm font-medium">New Chat</span>
          )}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-2 px-3 space-y-1">
        {isLoading ? (
          <ConversationListSkeleton count={5} />
        ) : conversations.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center text-gray-500 text-sm py-4"
          >
            {!isCollapsed && "No conversations yet"}
          </motion.div>
        ) : (
          <AnimatePresence mode="popLayout">
            {conversations.map((conv, index) => {
              const isActive = conv.id === currentConversationId;
              const title = getConversationTitle(conv);
              const timeLabel = formatRelativeTime(conv.updated_at);

              return (
                <motion.button
                  key={conv.id}
                  custom={index}
                  variants={itemVariants}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                  layout
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onSelectConversation?.(conv.id)}
                  className={clsx(
                    "flex items-center gap-3 w-full p-2 rounded-md transition-colors text-left group",
                    isCollapsed ? "justify-center" : "justify-start",
                    isActive
                      ? "bg-gray-800 text-white"
                      : "text-gray-400 hover:text-white hover:bg-gray-800",
                  )}
                  title={!isCollapsed ? undefined : title}
                >
                  <MessageSquare size={16} className="shrink-0" />
                  <AnimatePresence>
                    {!isCollapsed && (
                      <motion.div
                        initial={{ opacity: 0, width: 0 }}
                        animate={{ opacity: 1, width: "auto" }}
                        exit={{ opacity: 0, width: 0 }}
                        className="flex-1 min-w-0 overflow-hidden"
                      >
                        <span className="text-sm truncate block">{title}</span>
                        <span className="text-xs text-gray-500 truncate block">
                          {timeLabel}
                        </span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.button>
              );
            })}
          </AnimatePresence>
        )}
      </div>

      <div className="p-3 border-t border-gray-800 space-y-1">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className={clsx(
            "flex items-center gap-3 w-full p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors",
            isCollapsed ? "justify-center" : "justify-start",
          )}
        >
          <Grid size={18} />
          <AnimatePresence>
            {!isCollapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                className="text-sm"
              >
                Apps
              </motion.span>
            )}
          </AnimatePresence>
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className={clsx(
            "flex items-center gap-3 w-full p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors",
            isCollapsed ? "justify-center" : "justify-start",
          )}
        >
          <Settings size={18} />
          <AnimatePresence>
            {!isCollapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                className="text-sm"
              >
                Settings
              </motion.span>
            )}
          </AnimatePresence>
        </motion.button>
      </div>
    </motion.div>
  );
};
