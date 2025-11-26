import React from "react";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import {
  Copy,
  ThumbsUp,
  ThumbsDown,
  Volume2,
  MoreHorizontal,
  RefreshCw,
} from "lucide-react";

interface MessageBubbleProps {
  role: "user" | "assistant" | "system";
  content: string;
  isFast?: boolean;
  latency?: string;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  role,
  content,
  isFast,
  latency,
}) => {
  const isUser = role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        "flex w-full mb-6",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={clsx(
          "max-w-[80%] md:max-w-[70%]",
          isUser ? "flex flex-col items-end" : "flex flex-col items-start",
        )}
      >
        <div
          className="px-5 py-3 rounded-2xl text-md leading-relaxed"
          style={
            isUser
              ? {
                  backgroundColor: "var(--color-surface-tertiary)",
                  color: "var(--color-text)",
                  borderBottomRightRadius: "0.125rem",
                }
              : {
                  color: "var(--color-text)",
                  paddingLeft: 0,
                }
          }
        >
          {content}
        </div>

        {!isUser && (
          <div
            className="flex items-center gap-3 mt-2"
            style={{ color: "var(--color-text-tertiary)" }}
          >
            <div className="flex gap-1">
              <ActionButton icon={<Copy size={14} />} label="Copy message" />
              <ActionButton
                icon={<ThumbsUp size={14} />}
                label="Good response"
              />
              <ActionButton
                icon={<ThumbsDown size={14} />}
                label="Bad response"
              />
              <ActionButton icon={<Volume2 size={14} />} label="Read aloud" />
              <ActionButton
                icon={<RefreshCw size={14} />}
                label="Regenerate response"
              />
              <ActionButton
                icon={<MoreHorizontal size={14} />}
                label="More options"
              />
            </div>
            {isFast && latency && (
              <span
                className="text-xs font-mono ml-auto"
                style={{ color: "var(--color-text-secondary)" }}
              >
                Fast • {latency}
              </span>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
};

const ActionButton = ({
  icon,
  label,
}: {
  icon: React.ReactNode;
  label: string;
}) => (
  <button
    className="p-1.5 rounded-md transition-colors hover:opacity-80"
    aria-label={label}
    title={label}
  >
    {icon}
  </button>
);
