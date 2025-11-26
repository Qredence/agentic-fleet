import React from "react";
import {
  Menu,
  Edit,
  MessageSquare,
  Image as ImageIcon,
  Users,
  Sun,
  Moon,
  Monitor,
  Plus,
  MoreHorizontal,
} from "lucide-react";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import { useTheme } from "../hooks/useTheme";

interface Conversation {
  id: string;
  title: string;
  timestamp: Date;
  preview?: string;
}

interface SidebarProps {
  isOpen: boolean;
  toggleSidebar: () => void;
  conversations?: Conversation[];
  activeConversationId?: string;
  onNewConversation?: () => void;
  onSelectConversation?: (id: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  toggleSidebar,
  conversations = [],
  activeConversationId,
  onNewConversation,
  onSelectConversation,
}) => {
  const { theme, setTheme } = useTheme();

  const toggleTheme = () => {
    if (theme === "light") setTheme("dark");
    else if (theme === "dark") setTheme("system");
    else setTheme("light");
  };

  const getThemeIcon = () => {
    switch (theme) {
      case "light":
        return <Sun size={18} />;
      case "dark":
        return <Moon size={18} />;
      case "system":
        return <Monitor size={18} />;
    }
  };

  const getThemeLabel = () => {
    switch (theme) {
      case "light":
        return "Light Mode";
      case "dark":
        return "Dark Mode";
      case "system":
        return "System";
    }
  };

  return (
    <motion.div
      className={clsx(
        "fixed left-0 top-0 h-full z-50 flex flex-col transition-all duration-300 ease-in-out",
        isOpen ? "w-64" : "w-0 opacity-0 pointer-events-none",
      )}
      style={{
        backgroundColor: "var(--color-surface)",
        borderRight: "1px solid var(--gray-200)",
      }}
      initial={false}
      animate={{ width: isOpen ? 256 : 0, opacity: isOpen ? 1 : 0 }}
    >
      <div className="p-4 flex items-center justify-between">
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-md transition-colors hover:opacity-80"
          style={{ color: "var(--color-text-secondary)" }}
        >
          <Menu size={20} />
        </button>
        <button
          className="p-2 rounded-md transition-colors hover:opacity-80"
          style={{ color: "var(--color-text-secondary)" }}
        >
          <Edit size={20} />
        </button>
      </div>

      <nav className="px-2 py-4 space-y-2">
        <NavItem
          icon={<MessageSquare size={18} />}
          label="Agentic Fleet"
          active
        />
        <NavItem icon={<ImageIcon size={18} />} label="Fleets" />
        <NavItem icon={<Users size={18} />} label="Companions" />
      </nav>

      {/* Conversations Section */}
      <div className="flex-1 flex flex-col min-h-0 px-2">
        <div className="flex items-center justify-between py-2 px-2">
          <span
            className="text-xs font-semibold uppercase tracking-wider"
            style={{ color: "var(--color-text-muted)" }}
          >
            Conversations
          </span>
          <button
            onClick={onNewConversation}
            className="p-1 rounded transition-colors hover:opacity-80"
            style={{ color: "var(--color-text-secondary)" }}
            title="New conversation"
          >
            <Plus size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1 pb-2">
          {conversations.length === 0 ? (
            <p
              className="text-xs px-2 py-4 text-center"
              style={{ color: "var(--color-text-muted)" }}
            >
              No conversations yet
            </p>
          ) : (
            conversations.map((conversation) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
                isActive={conversation.id === activeConversationId}
                onClick={() => onSelectConversation?.(conversation.id)}
              />
            ))
          )}
        </div>
      </div>

      <div className="p-4" style={{ borderTop: "1px solid var(--gray-200)" }}>
        <button
          onClick={toggleTheme}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors hover:opacity-80"
          style={{ color: "var(--color-text-secondary)" }}
        >
          {getThemeIcon()}
          <span>{getThemeLabel()}</span>
        </button>
      </div>
    </motion.div>
  );
};

const NavItem = ({
  icon,
  label,
  active = false,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
}) => (
  <button
    className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
    style={{
      backgroundColor: active
        ? "var(--color-surface-secondary)"
        : "transparent",
      color: active ? "var(--color-text)" : "var(--color-text-secondary)",
    }}
  >
    {icon}
    <span>{label}</span>
  </button>
);

const ConversationItem = ({
  conversation,
  isActive,
  onClick,
}: {
  conversation: Conversation;
  isActive: boolean;
  onClick: () => void;
}) => {
  const formatDate = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return "Today";
    if (days === 1) return "Yesterday";
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <button
      onClick={onClick}
      className={clsx(
        "w-full group flex items-center gap-2 px-2 py-2 rounded-lg text-sm transition-colors text-left",
      )}
      style={{
        backgroundColor: isActive
          ? "var(--color-surface-secondary)"
          : "transparent",
        color: isActive ? "var(--color-text)" : "var(--color-text-secondary)",
      }}
    >
      <MessageSquare
        size={14}
        className="shrink-0"
        style={{ color: "var(--color-text-muted)" }}
      />
      <div className="flex-1 min-w-0">
        <p
          className="truncate font-medium"
          style={{
            color: isActive
              ? "var(--color-text)"
              : "var(--color-text-secondary)",
          }}
        >
          {conversation.title}
        </p>
        <p
          className="text-xs truncate"
          style={{ color: "var(--color-text-muted)" }}
        >
          {formatDate(conversation.timestamp)}
        </p>
      </div>
      <button
        className="opacity-0 group-hover:opacity-100 p-1 rounded transition-opacity hover:opacity-80"
        style={{ color: "var(--color-text-muted)" }}
        onClick={(e) => {
          e.stopPropagation();
          // TODO: Add menu for rename/delete
        }}
      >
        <MoreHorizontal size={14} />
      </button>
    </button>
  );
};
